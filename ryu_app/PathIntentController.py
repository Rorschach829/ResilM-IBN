# PathIntentController.py

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet
from ryu.topology import event
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
import requests
from webob import Response
import json

INTENT_INSTANCE_NAME = 'intent_api_app'
INTENT_REST_PATH = '/intent/flow'


class PathIntentController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(PathIntentController, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        self.topology_api_app = self

        self.switches = {}
        self.ports = {}
        self.host_mac_table = {}
        self.mac_to_host_table = {}
        self.valid_hosts = set()
        self.seen_invalid_macs = set()

        wsgi.register(IntentRestAPI, {INTENT_INSTANCE_NAME: self})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.switches[datapath.id] = datapath
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto

        # ✅ 安装默认 miss-flow 表项：转发给控制器
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=0,
                                match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(event.EventLinkAdd)
    def link_add_handler(self, ev):
        src_dpid = ev.link.src.dpid
        dst_dpid = ev.link.dst.dpid
        self.ports[(src_dpid, dst_dpid)] = ev.link.src.port_no

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        src = str(eth.src).lower()
        dst = str(eth.dst).lower()

        # ✅ 忽略广播和 LLDP 包
        if dst == "ff:ff:ff:ff:ff:ff" or dst.startswith("01:80:c2"):
            return

        # ✅ 已学习则跳过
        if src in self.mac_to_host_table:
            return

        # ✅ 学习主机数量限制
        if len(self.host_mac_table) >= len(self.valid_hosts):
            if src not in self.seen_invalid_macs:
                self.logger.warning(f"⚠️ 未知主机 MAC: {src}，已达到主机上限")
                self.seen_invalid_macs.add(src)
            return

        # ✅ 分配 h1-hN 名称
        for hname in sorted(self.valid_hosts):
            if hname not in self.host_mac_table:
                self.host_mac_table[hname] = src
                self.mac_to_host_table[src] = hname
                self.logger.info(f"📌 学习到主机: {hname} -> {src}")
                break

    def install_path_flow(self, src_mac, dst_mac, path, match_fields, actions_str, priority):
        for i in range(len(path) - 1):
            curr = path[i]
            nxt = path[i + 1]

            if curr.startswith('h') or nxt.startswith('h'):
                self.logger.info(f"⏭️ 跳过非交换机段: {curr} -> {nxt}")
                continue

            try:
                curr_dpid = int(curr[1:])
                next_dpid = int(nxt[1:])
            except ValueError:
                self.logger.warning(f"❌ 非法节点名称: {curr}, {nxt}")
                continue

            datapath = self.switches.get(curr_dpid)
            if not datapath:
                self.logger.warning(f"❌ Datapath {curr_dpid} not found")
                continue

            out_port = self.ports.get((curr_dpid, next_dpid))
            if out_port is None:
                self.logger.warning(f"❌ No link from {curr_dpid} to {next_dpid}")
                continue

            parser = datapath.ofproto_parser
            ofproto = datapath.ofproto

            match_dict = {"eth_src": src_mac, "eth_dst": dst_mac}
            for k, v in match_fields.items():
                match_dict["eth_type" if k == "dl_type" else k] = v

            match = parser.OFPMatch(**match_dict)
            actions = [] if actions_str.upper() == "DENY" else [parser.OFPActionOutput(out_port)]
            inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
            datapath.send_msg(mod)

            self.logger.info(f"✅ 下发: {curr}({curr_dpid}) → {nxt}({next_dpid}) | port={out_port}")


class IntentRestAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(IntentRestAPI, self).__init__(req, link, data, **config)
        self.intent_app = data[INTENT_INSTANCE_NAME]

    @route('intent', INTENT_REST_PATH, methods=['POST'])
    def install_intent_flow(self, req, **kwargs):
        try:
            body = req.json if req.body else {}
            print(f"\n[DEBUG] 收到路径意图请求:\n{json.dumps(body, indent=2)}\n")
            src_host = body.get("source")
            dst_host = body.get("target")
            path = body.get("path")
            extra = body.get("extra", {})
            match_fields = extra.get("match", {})
            actions_str = extra.get("actions", "ALLOW")
            priority = extra.get("priority", 100)

            if not (src_host and dst_host and path):
                return Response(status=400, body="❌ 缺少必要字段")

            src_mac = self.intent_app.host_mac_table.get(src_host)
            dst_mac = self.intent_app.host_mac_table.get(dst_host)

            if not src_mac or not dst_mac:
                return Response(status=400, body=f"❌ 无法找到主机 MAC: {src_host}({src_mac}), {dst_host}({dst_mac})")

            self.intent_app.install_path_flow(src_mac, dst_mac, path, match_fields, actions_str, priority)
            return Response(status=200, body=f"✅ 成功安装流表: {src_host} -> {dst_host} via {path}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(status=500, body=f"❌ 控制器异常: {str(e)}")

    @route('intent', '/intent/valid_hosts', methods=['POST'])
    def register_valid_hosts(self, req, **kwargs):
        try:
            body = req.json
            hosts = body.get("hosts", [])
            new_hosts_set = set(hosts)

            print(f"📥 注册合法主机列表: {hosts}")

            if new_hosts_set != self.intent_app.valid_hosts:
                self.intent_app.valid_hosts = new_hosts_set
                self.intent_app.host_mac_table.clear()
                self.intent_app.mac_to_host_table.clear()
                self.intent_app.seen_invalid_macs.clear()
                self.intent_app.logger.info("✅ 已清空主机学习缓存，准备重新学习")
            else:
                self.intent_app.logger.info("📎 合法主机列表未变化，跳过清空学习缓存")

            return Response(status=200, body=json.dumps({
                "message": "✅ 合法主机注册成功",
                "valid_hosts": hosts
            }))
        except Exception as e:
            return Response(status=500, body=f"❌ 注册失败: {str(e)}")
