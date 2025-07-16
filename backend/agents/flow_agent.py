import requests
import json
from backend.utils.ryu_utils import get_all_switch_ids
from backend.utils.utils import convert_switch_name_to_dpid
from backend.net_simulation.ryu_controller import send_flow_mod
import backend.net_simulation.mininet_manager as mm
class FlowAgent:
    def install_flowtable(self, instruction: dict) -> str:
        flow_rule = {
            "dpid": 1,  # 默认交换机ID，可拓展支持多个
            "match": instruction.get("extra", {}).get("match", {}),
            "actions": [],
            "priority": instruction.get("extra", {}).get("priority", 100)
        }

        if instruction.get("extra", {}).get("actions") == "DENY":
            if send_flow_mod(flow_rule):
                return f"✅ 流表下发成功 (阻断 {flow_rule['match']})"
            else:
                return "❌ 流表下发失败"

    def delete_flowtable(self, instruction: dict) -> str:
        switches = instruction.get("switches", [])
        match = instruction.get("extra", {}).get("match") or instruction.get("match", {})

        if not switches:
            return "❌ 错误：未指定交换机"

        for sw in switches:
            sw_list = get_all_switch_ids() if sw == "all" else [int(sw.replace("s", ""))]

            for dpid in sw_list:
                payload = {"dpid": dpid, "match": match}
                try:
                    resp = requests.post("http://localhost:8081/stats/flowentry/delete", json=payload)
                    if resp.status_code != 200:
                        return f"❌ 删除流表失败，交换机 {dpid} 返回码 {resp.status_code}"
                except Exception as e:
                    return f"❌ 删除流表失败: {e}"
        return "✅ 流表删除成功"

    def get_flowtable(self, instruction: dict) -> str:
        switches = instruction.get("switches", [])
        results = []
        for sw in switches:
            dpid = convert_switch_name_to_dpid(sw)
            url = f"http://localhost:8081/stats/flow/{dpid}"
            try:
                resp = requests.get(url)
                if resp.status_code == 200:
                    flows = resp.json().get(str(dpid), [])
                    formatted = json.dumps(flows, indent=2, ensure_ascii=False)
                    results.append(f"✅ 交换机 {sw} 当前流表:\n{formatted}")
                else:
                    results.append(f"❌ 无法获取交换机 {sw} 的流表")
            except Exception as e:
                results.append(f"❌ 请求失败: {e}")
        return "\n\n".join(results)

    def limit_bandwidth(self, instruction: dict) -> str:
        src = instruction.get("src_host")
        dst = instruction.get("dst_host")
        rate = instruction.get("rate_mbps")

        if not mm.global_net:
            return "❌ 当前没有拓扑"

        src_host = mm.global_net.get(src)
        if not src_host:
            return f"❌ 找不到主机 {src}"

        try:
            dev = f"{src}-eth0"
            rate_str = f"{rate}mbit"
            cmds = [f"tc qdisc del dev {dev} root"]

            if dst:
                dst_host = mm.global_net.get(dst)
                if not dst_host:
                    return f"❌ 找不到目标主机 {dst}"
                dst_ip = dst_host.IP()

                cmds += [
                    f"tc qdisc add dev {dev} root handle 1: htb default 12",
                    f"tc class add dev {dev} parent 1: classid 1:1 htb rate {rate_str}",
                    f"tc filter add dev {dev} protocol ip parent 1: prio 1 u32 match ip dst {dst_ip} flowid 1:1"
                ]
                result = f"✅ 设置限速：{src} → {dst} = {rate}Mbps"
            else:
                cmds += [
                    f"tc qdisc add dev {dev} root tbf rate {rate_str} burst 20kb latency 70ms"
                ]
                result = f"✅ 设置全局限速：{src} = {rate}Mbps"

            for c in cmds:
                src_host.cmd(c)
            return result

        except Exception as e:
            return f"❌ 限速失败: {e}"


    def clear_bandwidth_limit(self, instruction: dict) -> str:
        host = instruction.get("host")

        if not mm.global_net:
            return "❌ 当前没有拓扑"

        target = mm.global_net.get(host)
        if not target:
            return f"❌ 主机 {host} 不存在"

        try:
            dev = f"{host}-eth0"
            cmd = f"tc qdisc del dev {dev} root"
            result = target.cmd(cmd)
            return f"✅ 已取消限速：{host}\n执行结果:\n{result}"
        except Exception as e:
            return f"❌ 取消限速失败: {e}"
