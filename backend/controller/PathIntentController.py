from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, arp, ipv4
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.controller import dpset
from webob import Response
import networkx as nx
import json

# 全局变量传给 REST 控制器
intent_instance_name = 'intent_api_app'

class PathIntentController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = { 'wsgi': WSGIApplication }

    def __init__(self, *args, **kwargs):
        super(PathIntentController, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        self.mac_to_port = {}
        self.hosts = {}  # IP -> (DPID, Port, MAC)
        self.net = nx.DiGraph()
        self.dpset = kwargs['dpset']

        wsgi.register(IntentWebController, {intent_instance_name: self})

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

        if src not in self.hosts:
            self.logger.info(f"注册新主机: {src} (dpid={dpid}, port={in_port})")
            self.hosts[src] = (dpid, in_port, src)

        # flooding only for ARP
        if pkt.get_protocol(arp.arp):
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=in_port,
                actions=[parser.OFPActionOutput(ofproto.OFPP_FLOOD)],
                data=msg.data
            )
            datapath.send_msg(out)
            return
    @set_ev_cls(event.EventLinkAdd)
    def update_links(self, ev):
        link = ev.link
        src = link.src
        dst = link.dst

        self.net.add_edge(src.dpid, dst.dpid, port=src.port_no)
        self.net.add_edge(dst.dpid, src.dpid, port=dst.port_no)

        self.logger.info(f"✅ update_links链路已添加: {src.dpid} <--> {dst.dpid}")
        self.logger.info(f"✅ update links当前 NetworkX 图的边: {self.net.edges(data=True)}")
    @set_ev_cls(event.EventSwitchEnter)
    def get_topology_data(self, ev):
        switch_list = get_switch(self, None)
        self.net.add_nodes_from([sw.dp.id for sw in switch_list])

        link_list = get_link(self, None)
        for link in link_list:
            src = link.src.dpid
            dst = link.dst.dpid
            self.logger.info(f"Link: {src} -> {dst}")
            self.net.add_edge(src, dst, port=link.src.port_no)
            self.net.add_edge(dst, src, port=link.dst.port_no)

        # 新增打印
        self.logger.info(f"当前 NetworkX 图的节点: {list(self.net.nodes)}")
        self.logger.info(f"当前 NetworkX 图的边: {list(self.net.edges)}")

    def install_path_between_hosts(self, src_host: str, dst_host: str):
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

        src_dpid, src_port, _ = self.hosts[src_mac]
        dst_dpid, dst_port, _ = self.hosts[dst_mac]

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

        # 添加主机默认接入流表（以便非路径流量也能送到主机）
        for mac, (dpid, port, _) in self.hosts.items():
            dp = self.get_datapath(dpid)
            match = dp.ofproto_parser.OFPMatch(eth_dst=mac)
            actions = [dp.ofproto_parser.OFPActionOutput(port)]
            self.add_flow(dp, 1, match, actions)
            self.logger.info(f"🔁 添加主机接入流表: dpid={dpid}, dst={mac}, out_port={port}")

    

    def get_datapath(self, dpid):
        for dp_id, dp in self.dpset.get_all():
            if dp.id == dpid:
                return dp
        raise Exception(f"找不到对应的datapath: {dpid}")

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

