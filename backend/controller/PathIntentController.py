from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, arp, ipv4
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.controller import dpset
from webob import Response
# from backend.net_simulation import net_bridge

import networkx as nx
import json
import traceback
import select 

print("[DEBUG] select.poll:", hasattr(select, "poll"))

import ryu.lib.hub as hub
print("[DEBUG] 当前 hub 使用:", hub.__file__)


# 修复 eventlet/gevent 等污染的 select 模块
import sys
import importlib
if "select" in sys.modules:
    del sys.modules["select"]
 # 强制导入标准库

# 全局变量传给 REST 控制器
intent_instance_name = 'intent_api_app'

class PathIntentController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    # _CONTEXTS = { 'wsgi': WSGIApplication }
    _CONTEXTS = {
        'wsgi': WSGIApplication,
        'dpset': dpset.DPSet
    }
    _NAME = "PathIntentController"  # ✅ 命名用于 lookup

    # 初始化，维护主机表、拓扑图、交换机数据、Mininet句柄等
    def __init__(self, *args, **kwargs):
        super(PathIntentController, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        self.mac_to_port = {}
        self.hosts = {}  # IP -> (DPID, Port, MAC)
        self.net = nx.DiGraph()
        self.dpset = kwargs['dpset']
        self.mininet_net = None
        self.datapaths = {} # ✅ 用于记录连接的交换机 datapath

        wsgi.register(IntentWebController, {intent_instance_name: self})
        self.logger.info("[DEBUG] PathIntentController 初始化成功")
        self.logger.info(f"当前控制器注册名: {self.name}")

        # 安装默认流表
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # 安装默认规则：所有未知包发到控制器
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.logger.info(f"[FlowInit] 安装默认流表规则，将未知流量送至控制器 (dpid={datapath.id})")

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst)
        datapath.send_msg(mod)
        self.logger.info(f"🚀 add_flow called on dpid={datapath.id}, match={match}, actions={actions}")

        # 主机自动注册/学习
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        dpid = datapath.id
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        dst = eth.dst
        src = eth.src

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        src_mac = src.lower()

        # === 主机注册增强逻辑 ===

        # 跳过广播、组播、STP MAC
        if src_mac.startswith("ff:ff") or src_mac.startswith("01:80:c2") or src_mac.startswith("33:33"):
            self.logger.debug(f"[过滤] 忽略非法源 MAC: {src_mac}")
            return

        # === 只处理 ARP 或 IPv4 包，且 IP 必须在合法网段 ===
        from ryu.lib.packet import arp, ipv4
        arp_pkt = pkt.get_protocol(arp.arp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)

        if arp_pkt:
            src_ip = arp_pkt.src_ip
        elif ipv4_pkt:
            src_ip = ipv4_pkt.src
        else:
            self.logger.debug(f"[过滤] 非 ARP/IP 包，跳过主机注册: {src_mac}")
            return

        if not src_ip.startswith("10.0.0."):
            self.logger.debug(f"[过滤] 非法主机 IP ({src_ip})，跳过注册: {src_mac}")
            return

        # 已注册则检查是否重复注册
        if src_mac in self.hosts:
            old_dpid, old_port, _ = self.hosts[src_mac]
            if old_dpid == dpid and old_port == in_port:
                return
            else:
                self.logger.debug(f"[主机重复学习] 已存在 {src_mac}，忽略新位置 dpid={dpid}, port={in_port}")
                return

        # 注册主机
        self.logger.info(f"✅ 注册新主机: {src_mac} (dpid={dpid}, port={in_port}, ip={src_ip})")
        self.hosts[src_mac] = (dpid, in_port, src_mac)

        # flooding only for ARP
        if arp_pkt:
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=in_port,
                actions=[parser.OFPActionOutput(ofproto.OFPP_FLOOD)],
                data=msg.data
            )
            datapath.send_msg(out)
            return

        # 监听新链路，更新拓扑
    @set_ev_cls(event.EventLinkAdd)
    def update_links(self, ev):
        link = ev.link
        src = f"s{link.src.dpid}"
        dst = f"s{link.dst.dpid}"

        self.net.add_edge(src, dst, port=link.src.port_no)
        self.net.add_edge(dst, src, port=link.dst.port_no)

        self.logger.info(f"✅ 链路已添加: {src} <--> {dst}")
        self.logger.info(f"✅ 当前 NetworkX 图的边: {self.net.edges(data=True)}")


    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):
        switch_list = get_switch(self, None)
        self.net.add_nodes_from([f"s{sw.dp.id}" for sw in switch_list])

        link_list = get_link(self, None)
        for link in link_list:
            src = f"s{link.src.dpid}"
            dst = f"s{link.dst.dpid}"
            self.net.add_edge(src, dst, port=link.src.port_no)
            self.net.add_edge(dst, src, port=link.dst.port_no)

        self.logger.info(f"当前 NetworkX 图的节点: {list(self.net.nodes)}")
        self.logger.info(f"当前 NetworkX 图的边: {list(self.net.edges)}")


         # 计算最短路径并批量下发流表（双向）
    def install_path_between_hosts(self, src_host: str, dst_host: str):

                # 检查路径图中是否存在未注册的 DPID
        registered_dpids = set(self.datapaths.keys())
        all_path_dpids = set(self.net.nodes())

        invalid_dpids = all_path_dpids - registered_dpids
        if invalid_dpids:
            self.logger.error(f"[❌错误] NetworkX 图中存在未连接的 DPID: {invalid_dpids}")
            raise Exception(f"网络图中包含未注册交换机 DPID: {invalid_dpids}")

        self.logger.info(f"📌 [注册主机总数]: {len(self.hosts)}")
        self.logger.info(f"📌 [主机注册信息]:")
        for mac, (dpid, port, _) in self.hosts.items():
            self.logger.info(f"    MAC={mac}, DPID={dpid}, Port={port}")

        self.logger.info(f"准备下发路径：src_host={src_host}, dst_host={dst_host}")
        self.logger.info(f"当前已注册主机: {list(self.hosts.keys())}")

        src_mac = src_host.lower()
        dst_mac = dst_host.lower()

        if src_mac not in self.hosts or dst_mac not in self.hosts:
            raise Exception("源或目标主机未注册")

        # src_dpid, src_port, _ = self.hosts[src_mac]
        # dst_dpid, dst_port, _ = self.hosts[dst_mac]
        src_dpid_num, src_port, _ = self.hosts[src_mac]
        dst_dpid_num, dst_port, _ = self.hosts[dst_mac]

        src_dpid = f"s{src_dpid_num}"
        dst_dpid = f"s{dst_dpid_num}"


        self.logger.info(f"✅ 当前 NetworkX 图的节点: {self.net.nodes()}")
        self.logger.info(f"✅ 当前 NetworkX 图的边: {self.net.edges(data=True)}")

        path = nx.shortest_path(self.net, src_dpid, dst_dpid)
        self.logger.info(f"路径: {src_mac}({src_dpid}) → {dst_mac}({dst_dpid}): {path}")

        # 下发正向路径流表
        for i in range(len(path)):
            cur = path[i]
            if i == len(path) - 1:
                # 最后一跳：交换机到目的主机
                out_port = self.hosts[dst_mac][1]
                self.logger.info(f"➡️ [正向] 最后一跳: dpid={cur} → 主机 {dst_mac}, 使用注册端口 {out_port}")
            else:
                nex = path[i + 1]
                out_port = self.net[cur][nex]['port']
                self.logger.info(f"➡️ [正向] dpid={cur} → dpid={nex}, out_port={out_port}")

            dp = self.get_datapath(cur)
            match = dp.ofproto_parser.OFPMatch(eth_src=src_mac, eth_dst=dst_mac)
            actions = [dp.ofproto_parser.OFPActionOutput(out_port)]
            self.add_flow(dp, 1, match, actions)
            self.logger.info(f"🚀 下发正向流表: dpid={cur}, src={src_mac}, dst={dst_mac}, out_port={out_port}")

        # 下发回程路径流表
        for i in range(len(path) - 1, -1, -1):
            cur = path[i]
            if i == 0:
                out_port = self.hosts[src_mac][1]
                self.logger.info(f"↩️ [回程] 最后一跳: dpid={cur} → 主机 {src_mac}, 使用注册端口 {out_port}")
            else:
                pre = path[i - 1]
                out_port = self.net[cur][pre]['port']
                self.logger.info(f"↩️ [回程] dpid={cur} → dpid={pre}, out_port={out_port}")

            dp = self.get_datapath(cur)
            match = dp.ofproto_parser.OFPMatch(eth_src=dst_mac, eth_dst=src_mac)
            actions = [dp.ofproto_parser.OFPActionOutput(out_port)]
            self.add_flow(dp, 1, match, actions)
            self.logger.info(f"🚀 下发回程流表: dpid={cur}, src={dst_mac}, dst={src_mac}, out_port={out_port}")

        # 添加主机默认接入流表（以便非路径流量也能送到主机）★7.13这一天的目的就是为了让gpt写出下面这几行。气死我了。
        for mac, (dpid, port, _) in self.hosts.items():
            dp = self.get_datapath(dpid)
            match = dp.ofproto_parser.OFPMatch(eth_dst=mac)
            actions = [dp.ofproto_parser.OFPActionOutput(port)]
            self.add_flow(dp, 1, match, actions)
            self.logger.info(f"🔁 添加主机接入流表: dpid={dpid}, dst={mac}, out_port={port}")


    def get_datapath(self, dpid):
        if isinstance(dpid, str) and dpid.startswith("s"):
            dpid_num = int(dpid[1:])
        else:
            dpid_num = int(dpid)

        for dp_id, dp in self.dpset.get_all():
            if dp.id == dpid_num:
                return dp
        raise Exception(f"找不到对应的 datapath: {dpid}")

        # 交换机上线/下线的状态维护与清理
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if dp.id not in self.datapaths:
                self.logger.info(f"✅ 新交换机上线: DPID={dp.id}")
            # self.datapaths[dp.id] = dp
            self.datapaths[f"s{dp.id}"] = dp
        elif ev.state == DEAD_DISPATCHER:
            dpid = dp.id
            if dpid in self.datapaths:
                self.logger.warning(f"❌ 交换机离线: DPID={dpid}，正在清除相关状态...")

                # 1. 删除 datapath 引用
                del self.datapaths[dpid]

                # 2. 清除主机列表中挂在该交换机下的主机
                to_remove = [mac for mac, (d, _, _) in self.hosts.items() if d == dpid]
                for mac in to_remove:
                    del self.hosts[mac]
                    self.logger.info(f"🧹 主机已移除: {mac} (原挂在 DPID={dpid})")

                # 3. 清除 NetworkX 拓扑图中节点
                if dpid in self.net:
                    self.net.remove_node(dpid)
                    self.logger.info(f"🧹 NetworkX 图中移除节点: DPID={dpid}")

                self.logger.info(f"✅ 状态清除完成: DPID={dpid}")    
    
        # 断开链路，NetworkX图和Mininet同步
    def link_down(self, src_switch: str, dst_switch: str):
        from backend.net_simulation import net_bridge  # 确保你引入了

        self.logger.info("以下消息由link_down方法输出")
        self.logger.debug(f"当前 NetworkX 图边数量: {self.net.number_of_edges()}")

        net = net_bridge.global_net  # ✅ 最优解：直接从共享全局变量中读取
        print("[RYU] net_bridge.global_net id:", id(net_bridge.global_net))

        if not net:
            print("⚠️[RYU] Mininet 实例未创建，跳过实际断链")
            return "Mininet not ready"

        try:
            self.logger.info(f"🚧 准备断开链路: {src_switch} ↔ {dst_switch}")

            # 1. 更新 NetworkX 拓扑图
            if self.net.has_edge(src_switch, dst_switch):
                self.net.remove_edge(src_switch, dst_switch)
                self.logger.info(f"🧠 拓扑图中已删除边: {src_switch} ↔ {dst_switch}")
            else:
                self.logger.warning(f"⚠️ 拓扑图中未找到边: {src_switch} ↔ {dst_switch}")

            # 2. 真正断开 Mininet 中链路
            link = net.linksBetween(
                net.get(src_switch),
                net.get(dst_switch)
            )
            if link:
                link_obj = link[0]
                link_obj.intf1.ifconfig('down')
                link_obj.intf2.ifconfig('down')
                self.logger.info(f"✅ Mininet 中链路已禁用: {src_switch} ↔ {dst_switch}")
                if link_obj in net.links:
                    net.links.remove(link_obj)
                    self.logger.info(f"🧹 Mininet 中 link 对象已移除")
            else:
                self.logger.warning(f"⚠️ Mininet 中未找到链路: {src_switch} ↔ {dst_switch}")

        except Exception as e:
            self.logger.error(f"❌ 链路断开失败: {e}")
            self.logger.error(traceback.format_exc())


    # 重置控制器状态
    def reset_state(self):
        self.logger.info("[RESET] 正在清空控制器状态")
        self.hosts.clear()
        self.net.clear()
        self.datapaths.clear()
        self.logger.info("[RESET] 控制器状态清空完毕")



class IntentWebController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super().__init__(req, link, data, **config)
        self.intent_app = data[intent_instance_name]

    @route('install_path', '/intent/flow', methods=['POST'])
    def install_path(self, req, **kwargs):
        try:
            content = req.json if req.body else {}
            src = content.get('src_host')
            dst = content.get('dst_host')
            if not src or not dst:
                return Response(
                    status=400,
                    body="src_host 或 dst_host 参数缺失",
                    content_type='text/plain; charset=UTF-8'
                )

            self.intent_app.logger.info(f"当前注册主机: {list(self.intent_app.hosts.keys())}")
            self.intent_app.install_path_between_hosts(src, dst)
            self.intent_app.install_path_between_hosts(dst, src)
            return Response(
                status=200,
                body=f"路径已安装: {src} → {dst}",
                content_type='text/plain; charset=UTF-8'
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                status=500,
                body=f"错误: {e}",
                content_type='text/plain; charset=UTF-8'
            )

    
    @route('valid_hosts', '/intent/valid_hosts', methods=['GET'])
    def get_valid_hosts(self, req, **kwargs):
        host_list = list(self.intent_app.hosts.keys())  # MAC 地址列表
        return Response(content_type='application/json',
                        body=json.dumps(host_list).encode('utf-8'))
    
    # 断开链路
    @route('link_down', '/intent/link_down', methods=['POST'])
    def link_down_api(self, req, **kwargs):
        print("[DEBUG] ✅RYU收到 /intent/link_down 请求")

        try:
            print("[DEBUG] 开始处理 /intent/link_down 的api请求")
            content = req.json if req.body else {}
            src, dst = content.get("link", [None, None])
            if not src or not dst:
                return Response(status=400, body="参数错误")

            # ❌ 删除旧代码：不要再导入 mm.global_net
            # ✅ mininet_net 由 Flask 注入 controller，直接使用
            self.intent_app.link_down(src, dst)
            return Response(status=200, body=f"✅ 链路断开成功: {src} ↔ {dst}")

        except Exception as e:
            print("[DEBUG] 链路断开失败堆栈:")
            traceback.print_exc()
            return Response(status=500, body=f"❌ 执行失败: {e}")