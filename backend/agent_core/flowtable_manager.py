# backend/utils/flowtable_manager.py
from typing import List, Dict, Any
import requests
import json
import backend.net_simulation.mininet_manager as mm
from backend.utils.utils import convert_switch_name_to_dpid
from backend.utils.ryu_utils import get_all_switch_ids
from backend.net_simulation.ryu_controller import send_flow_mod
from backend.utils.topology_utils import get_output_port, auto_fix_switches_by_intent,fix_switches_for_get_flowtable
from typing import Tuple, Optional, Dict,Any


class FlowTableManager:

    def install_rule(self, instruction: dict) -> Tuple[str, bool, Optional[int]]:
        if not instruction.get("switches") or instruction["switches"] == ["s1"]:
            auto_fix_switches_by_intent(instruction)

        switches = instruction.get("switches")
        results = []
        success_count = 0

        match = instruction.get("match") or instruction.get("extra", {}).get("match", {})
        action_flag = instruction.get("actions") or instruction.get("extra", {}).get("actions", "DENY")
        priority = instruction.get("priority") or instruction.get("extra", {}).get("priority", 100)

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
                "actions": []
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
                success_count += 1
            else:
                results.append(f"❌ 下发失败到 {sw}")

        all_ok = (success_count == len(switches))
        return "\n".join(results), all_ok, success_count

    from typing import Tuple, Optional, Dict, Any  # 确保导入这些类型

    def delete_rule(self, instruction: dict) -> Tuple[str, bool, Optional[int]]:
        results = []
        success_count = 0

        auto_fix_switches_by_intent(instruction)
        switches = instruction.get("switches", [])
        match = instruction.get("match", {}) or instruction.get("extra", {}).get("match", {})

        if not switches:
            return "❌ 参数错误：未提供交换机列表", False, None

        # ✅ 情况1：清空所有流表（无 match）
        if not match:
            for sw in switches:
                msg, ok = self._delete_all_flows(sw)
                results.append(msg)
                if ok:
                    success_count += 1
            all_ok = (success_count == len(switches))
            return "\n".join(results), all_ok, success_count

        # ✅ 情况2：删除特定 match（正反两个方向）
        src_ip = match.get("nw_src")
        dst_ip = match.get("nw_dst")
        proto = match.get("nw_proto")
        dl_type = match.get("dl_type")

        # 删除原方向
        for sw in switches:
            msg, ok = self._delete_on_switches(sw, match)
            results.append(msg)
            if ok:
                success_count += 1

        # 删除反方向
        if src_ip and dst_ip:
            reverse_match = {
                "nw_src": dst_ip,
                "nw_dst": src_ip,
                "nw_proto": proto,
                "dl_type": dl_type
            }
            for sw in switches:
                msg, ok = self._delete_on_switches(sw, reverse_match)
                results.append(msg)
                if ok:
                    success_count += 1

        total_attempts = len(switches) * (2 if src_ip and dst_ip else 1)
        all_ok = (success_count == total_attempts)

        return "\n".join(results), all_ok, success_count



    # 删除某交换机上所有流表
    def _delete_all_flows(self, sw: str) -> Tuple[str, bool]:
        try:
            dpid = convert_switch_name_to_dpid(sw)
        except ValueError as e:
            return f"❌ 无法识别交换机 {sw}: {e}", False

        payload = {
            "dpid": dpid,
            "match": {}  # 空 match 表示删除所有流表
        }

        try:
            print(f"[delete_rule] 正在清空 {sw} 上所有流表")
            resp = requests.post("http://localhost:8081/stats/flowentry/delete", json=payload)
            if resp.status_code != 200:
                return f"❌ 删除失败，交换机 {sw} 返回码 {resp.status_code}", False
        except Exception as e:
            return f"❌ 删除失败: {e}", False

        return f"✅ 清空 {sw} 上所有流表成功", True



    # 精确删除某条规则
    def _delete_on_switches(self, sw: str, match: Dict[str, Any]) -> Tuple[str, bool]:
        try:
            dpid = convert_switch_name_to_dpid(sw)
        except ValueError as e:
            return f"❌ 无法识别交换机 {sw}: {e}", False

        payload = {"dpid": dpid, "match": match}
        try:
            print(f"[delete_rule] 正在删除 {sw} 上匹配 {match}")
            resp = requests.post("http://localhost:8081/stats/flowentry/delete", json=payload)
            if resp.status_code != 200:
                return f"❌ 删除失败，交换机 {sw} 返回码 {resp.status_code}", False
        except Exception as e:
            return f"❌ 删除失败: {e}", False

        return f"✅ 删除匹配规则: {match}", True

    def query_table(self, instruction: dict) -> Tuple[str, bool, Optional[int]]:
        if not instruction.get("switches") or instruction["switches"] == ["s1"]:
            fix_switches_for_get_flowtable(instruction)

        switches = instruction.get("switches", [])
        results = []
        success_count = 0

        for sw in switches:
            try:
                dpid = convert_switch_name_to_dpid(sw)
                url = f"http://localhost:8081/stats/flow/{dpid}"
                resp = requests.get(url)
                if resp.status_code == 200:
                    flows = resp.json().get(str(dpid), [])
                    formatted = json.dumps(flows, indent=2, ensure_ascii=False)
                    results.append(f"✅ {sw} 流表:\n{formatted}")
                    success_count += 1
                else:
                    results.append(f"❌ 获取 {sw} 流表失败（状态码 {resp.status_code}）")
            except Exception as e:
                results.append(f"❌ 请求失败: {e}")

        all_ok = (success_count == len(switches))
        return "\n\n".join(results), all_ok, success_count

    def limit_bandwidth(self, instruction: dict) -> Tuple[str, bool, Optional[str]]:
        src = instruction.get("src_host")
        dst = instruction.get("dst_host")
        rate = instruction.get("rate_mbps")

        if not mm.global_net:
            return "❌ 当前没有拓扑", False, None

        src_host = mm.global_net.get(src)
        if not src_host:
            return f"❌ 找不到主机 {src}", False, None

        try:
            dev = f"{src}-eth0"
            rate_str = f"{rate}mbit"
            cmds = [f"tc qdisc del dev {dev} root"]

            if dst:
                dst_host = mm.global_net.get(dst)
                if not dst_host:
                    return f"❌ 找不到目标主机 {dst}", False, None
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

            return result, True, f"{rate} Mbps"

        except Exception as e:
            return f"❌ 限速失败: {e}", False, None

    def clear_bandwidth_limit(self, instruction: dict) -> Tuple[str, bool, Optional[str]]:
        host = instruction.get("host")
        if not mm.global_net:
            return "❌ 当前没有拓扑", False, None

        target = mm.global_net.get(host)
        if not target:
            return f"❌ 主机 {host} 不存在", False, None

        try:
            dev = f"{host}-eth0"
            cmd = f"tc qdisc del dev {dev} root"
            result = target.cmd(cmd)

            msg = f"✅ 已取消限速：{host}\n执行结果:\n{result}"
            return msg, True, host
        except Exception as e:
            return f"❌ 取消限速失败: {e}", False, None


