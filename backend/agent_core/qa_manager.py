# backend/agent_core/qa_manager.py
import time
from backend.net_simulation import mininet_manager as mm
import re
from backend.utils.topology_utils import get_path_switches, get_host_ip
from backend.coordinator.message_pool import message_pool
from typing import Optional, Tuple
from backend.utils.messagepool_utils import send_intent
class QAManager:

    def ping_test(self, instruction: dict) -> Tuple[str, Optional[dict]]:
        print(f"[DEBUG] global_net状态: {mm.global_net}")
        if not mm.global_net:
            return "❌ 当前没有拓扑 (请先创建拓扑或检查 global_net 引用)", None

        src_name = instruction.get("extra", {}).get("source") or instruction.get("source")
        target_ip = instruction.get("extra", {}).get("target") or instruction.get("target")
        target_host = instruction.get("extra", {}).get("target_host") or instruction.get("target")
        expect_result = instruction.get("extra", {}).get("expect_result", None)
        auto_fix = instruction.get("extra", {}).get("auto_fix", False)

        if not src_name or not target_ip:
            return "❌ 指令缺少 source 或 target", None

        src_host = mm.global_net.get(src_name)
        if not src_host:
            return f"❌ 主机 {src_name} 不存在", None

        print(f"[PING] 正在尝试: {src_name} -> {target_ip}")
        result = src_host.cmd("ping -c 3 -W 1 %s" % target_ip)
        match = re.search(r"(\d+) packets transmitted, (\d+) received", result)
        success = match and int(match.group(2)) >= 1

        final_result = "%s %s ping 通 %s\n%s" % (
            src_name, "可以✅" if success else "无法❌", target_host or target_ip, result)

        if success:
            return final_result, None

        # 失败 + 预期成功 + 自动修复开关开启 → 触发 QA 修复建议
        if expect_result == "success" and auto_fix:
            print("[QAAgent] ping 失败，准备提出自动修复建议")

            src_ip = get_host_ip(src_name)
            switches = get_path_switches(src_name, target_ip)
            match_fields = {
                "dl_type": 2048,
                "nw_src": src_ip,
                "nw_dst": target_ip,
                "nw_proto": 1
            }

            trace_id = instruction.get("trace_id")

            repair_suggestion = {
                "action": "repair_suggestion",
                "source": src_name,
                "target": target_ip,
                "switches": switches,
                "match": match_fields,
                "auto_fix": True,
                "reason": "QAAgent 检测 ping 失败，建议修复通信路径"
            }

            return final_result + "\n🧠 QAAgent 已提出修复建议", repair_suggestion

        return final_result, None


    def ping_all(self) -> str:
        if not mm.global_net:
            return "❌ 当前没有拓扑"
        net = mm.global_net
        try:
            print("=== 多线程双向ping_all测试===")
            from backend.utils.topology_utils import robust_ping_pairs_multi_thread

            res = robust_ping_pairs_multi_thread(mm.global_net)

            failed_pairs = res["failed_pairs"]
            total = res["total"]
            success = res["success"]

            if not failed_pairs:
                return f"✅ 所有主机均可互相通信，共测试 {total} 对"
            else:
                failed_lines = [f"- {src} → {dst}" for src, dst in failed_pairs]
                summary = f"✅ 其余 {success} 对主机通信正常"
                return "❌ 以下主机对无法通信：\n" + "\n".join(failed_lines) + "\n" + summary
      
        except Exception as e:
            return f"❌ 执行ping_all失败: {e}"

    def verify_bandwidth(self, instruction: dict) -> str:
        src = instruction.get("src_host")
        dst = instruction.get("dst_host")

        if not mm.global_net:
            return "❌ 当前没有拓扑"

        src_host = mm.global_net.get(src)
        dst_host = mm.global_net.get(dst)

        if not src_host or not dst_host:
            return f"❌ 找不到主机 {src} 或 {dst}"

        try:
            # 启动目标主机 iperf 服务器, TCP模式
            dst_host.cmd("iperf -s  -D")
            time.sleep(1)

            # 源主机发起 iperf 的TCP测试
            result = src_host.cmd(f"iperf -c {dst_host.IP()} -t 5")
            # return f"📊 带宽测试结果 (h1 → h2):\n{result}"
            return f"📊 带宽测试结果 ({src} → {dst}):\n{result}"

        except Exception as e:
            return f"❌ 带宽测试失败: {e}"

    def _get_host_by_ip(self, ip: str) -> str:
        """根据 IP 查找主机名"""
        net = mm.global_net
        for h in net.hosts:
            if h.IP() == ip:
                return h.name
        return "unknown"


