# backend/utils/flowtable_manager.py

import requests
import json
import backend.net_simulation.mininet_manager as mm
from backend.utils.utils import convert_switch_name_to_dpid
from backend.utils.ryu_utils import get_all_switch_ids
from backend.net_simulation.ryu_controller import send_flow_mod
from backend.utils.topology_utils import get_output_port, auto_fix_switches_by_intent

class FlowTableManager:

    def install_rule(self, instruction: dict) -> str:
        # 自动修复 switches
        if not instruction.get("switches") or instruction["switches"] == ["s1"]:
            auto_fix_switches_by_intent(instruction)

        switches = instruction.get("switches")
        results = []

        extra = instruction.get("extra", {})
        match = extra.get("match", {})
        action_flag = extra.get("actions", "DENY")
        priority = extra.get("priority", 100)

        for sw in switches:
            try:
                dpid = convert_switch_name_to_dpid(sw)
            except ValueError as e:
                results.append(f"❌ 无法识别交换机 {sw}: {e}")
                continue

            flow_rule = {
                "dpid": dpid,
                "match": match,
                "priority": priority,
                "actions": []  # 默认阻断
            }

            print(f"[flowtable_manager] action_flag为 {action_flag}")
            if action_flag == "ALLOW":
                try:
                    src_ip = match.get("nw_src")
                    dst_ip = match.get("nw_dst")
                    port = get_output_port(sw, dst_ip, mm)
                    if port is not None:
                        flow_rule["actions"] = [{"type": "OUTPUT", "port": port}]
                        print(f"[flowtable_manager] 出口端口为 {port}")
                    else:
                        print("[⚠️ Fallback] 找不到端口，改为 FLOOD")
                        flow_rule["actions"] = [{"type": "OUTPUT", "port": "FLOOD"}]
                except Exception as e:
                    print(f"[⚠️ 错误] 获取端口失败: {e}，改为 FLOOD")
                    flow_rule["actions"] = [{"type": "OUTPUT", "port": "FLOOD"}]

            if send_flow_mod(flow_rule):
                behavior = "转发" if flow_rule["actions"] else "阻断"
                results.append(f"✅ 成功下发到 {sw} ({behavior} {flow_rule['match']})")
            else:
                results.append(f"❌ 下发失败到 {sw}")

        return "\n".join(results)

    def delete_rule(self, instruction: dict) -> str:
        results = []

        # 自动修复 switch
        if not instruction.get("switches") or instruction["switches"] == ["s1"]:
            auto_fix_switches_by_intent(instruction)

        switches = instruction.get("switches", [])
        match = instruction.get("match", {}) or instruction.get("extra", {}).get("match", {})
        if not switches or not match:
            return "❌ 参数错误：未提供交换机或匹配字段"

        src_ip = match.get("nw_src")
        dst_ip = match.get("nw_dst")
        proto = match.get("nw_proto")
        dl_type = match.get("dl_type")

        # 删除原方向
        results.append(self._delete_on_switches(switches, match))

        # 反方向再来一次
        if src_ip and dst_ip:
            reverse_match = {
                "nw_src": dst_ip,
                "nw_dst": src_ip,
                "nw_proto": proto,
                "dl_type": dl_type
            }
            results.append(self._delete_on_switches(switches, reverse_match))

        return "\n".join(results)

    def _delete_on_switches(self, switches, match):
        for sw in switches:
            try:
                sw_list = get_all_switch_ids() if sw == "all" else [convert_switch_name_to_dpid(sw)]
            except ValueError as e:
                return f"❌ 无法识别交换机 {sw}: {e}"

            for dpid in sw_list:
                payload = {"dpid": dpid, "match": match}
                try:
                    resp = requests.post("http://localhost:8081/stats/flowentry/delete", json=payload)
                    if resp.status_code != 200:
                        return f"❌ 删除失败，交换机 {dpid} 返回码 {resp.status_code}"
                except Exception as e:
                    return f"❌ 删除失败: {e}"
        return f"✅ 已删除匹配规则: {match}"

    # def delete_rule(self, instruction: dict) -> str:
    #     # 自动修复 switches（和 install_rule 一致）
    #     if not instruction.get("switches") or instruction["switches"] == ["s1"]:
    #         auto_fix_switches_by_intent(instruction)

    #     switches = instruction.get("switches", [])
    #     match = instruction.get("match", {})

    #     if not switches or not match:
    #         return "❌ 参数错误：未提供交换机或匹配字段"

    #     for sw in switches:
    #         try:
    #             sw_list = get_all_switch_ids() if sw == "all" else [convert_switch_name_to_dpid(sw)]
    #         except ValueError as e:
    #             return f"❌ 无法识别交换机 {sw}: {e}"

    #         for dpid in sw_list:
    #             payload = {"dpid": dpid, "match": match}
    #             try:
    #                 resp = requests.post("http://localhost:8081/stats/flowentry/delete", json=payload)
    #                 if resp.status_code != 200:
    #                     return f"❌ 删除失败，交换机 {dpid} 返回码 {resp.status_code}"
    #             except Exception as e:
    #                 return f"❌ 删除失败: {e}"

    #     return "✅ 流表删除成功"


    def query_table(self, instruction: dict) -> str:
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
                    results.append(f"✅ {sw} 流表:\n{formatted}")
                else:
                    results.append(f"❌ 获取 {sw} 流表失败")
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
                result = f"✅ 限速：{src} → {dst} = {rate}Mbps"
            else:
                cmds += [
                    f"tc qdisc add dev {dev} root tbf rate {rate_str} burst 20kb latency 70ms"
                ]
                result = f"✅ 限速：{src} = {rate}Mbps"

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
