# backend/agent_core/qa_manager.py
import time
from backend.net_simulation import mininet_manager as mm
import re
from backend.utils.topology_utils import get_path_switches, get_host_ip
from backend.coordinator.message_pool import message_pool
from typing import Optional, Tuple
from backend.utils.messagepool_utils import send_intent
class QAManager:

    def ping_test(self, instruction: dict) -> Tuple[str, Optional[dict], bool]:
        print(f"[DEBUG] global_net状态: {mm.global_net}")
        if not mm.global_net:
            return "❌ 当前没有拓扑 (请先创建拓扑或检查 global_net 引用)", None, False

        src_name = instruction.get("extra", {}).get("source") or instruction.get("source")
        target_ip = instruction.get("extra", {}).get("target") or instruction.get("target")
        target_host = instruction.get("extra", {}).get("target_host") or instruction.get("target")
        expect_result = instruction.get("extra", {}).get("expect_result", None)
        auto_fix = instruction.get("extra", {}).get("auto_fix", False)

        if not src_name or not target_ip:
            return "❌ 指令缺少 source 或 target", None, False

        src_host = mm.global_net.get(src_name)
        if not src_host:
            return f"❌ 主机 {src_name} 不存在", None, False

        print(f"[PING] 正在尝试: {src_name} -> {target_ip}")
        result = src_host.cmd("ping -c 3 -W 1 %s" % target_ip)
        match = re.search(r"(\d+) packets transmitted, (\d+) received", result)
        success = match and int(match.group(2)) >= 1

        final_result = "%s %s ping 通 %s\n%s" % (
            src_name, "可以✅" if success else "无法❌", target_host or target_ip, result)

        # ✅ ping 成功：照旧返回 True，无需修改
        if success:
            return final_result, None, True

        # ✅ ping 失败 + 自动修复触发逻辑不变
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

            return final_result + "\n🧠 QAAgent 已提出修复建议", repair_suggestion, True  # ✅ 此处也改为 True

        # ✅ ping 失败但无异常，也认为执行成功（你现在想要的）
        return final_result, None, True


    
    def ping_all(self, instruction: dict) -> Tuple[str, bool, Optional[int]]:
        if not mm.global_net:
            return "❌ 当前没有拓扑", False, None

        try:
            from backend.utils.topology_utils import robust_ping_pairs_multi_thread

            print("=== 多线程双向 ping_all 测试 ===")
            net = mm.global_net
            res = robust_ping_pairs_multi_thread(net)

            failed_pairs = res["failed_pairs"]
            total = res["total"]
            success = res["success"]

            # ✅ 提取预期结果：希望通信成功（默认） or 失败（阻断）
            expect_result = instruction.get("extra", {}).get("expect_result", "success")
            expect_success = (expect_result == "success")
            actual_success = len(failed_pairs) == 0

            # ✅ 核心逻辑：实际结果 == 预期结果 → 判定为“成功的验证”
            is_result_ok = (actual_success == expect_success)

            # ✅ 构造日志信息
            if actual_success:
                msg = f"✅ 所有主机均可互相通信，共测试 {total} 对"
                return msg, is_result_ok, total
            else:
                failed_lines = [f"- {src} → {dst}" for src, dst in failed_pairs]
                summary = f"✅ 其余 {success} 对主机通信正常"
                msg = "❌ 以下主机对无法通信（共 %d 对）：" % len(failed_pairs) + "\n" + "\n".join(failed_lines) + "\n" + summary
                return msg, is_result_ok, len(failed_pairs)

        except Exception as e:
            return f"❌ 执行 ping_all 失败: {e}", False, None

    def verify_bandwidth(self, instruction: dict) -> Tuple[str, bool, Optional[str]]:
        src = instruction.get("src_host")
        dst = instruction.get("dst_host")

        if not mm.global_net:
            return "❌ 当前没有拓扑", False, None

        src_host = mm.global_net.get(src)
        dst_host = mm.global_net.get(dst)

        if not src_host or not dst_host:
            return f"❌ 找不到主机 {src} 或 {dst}", False, None

        try:
            # 启动目标主机 iperf 服务
            dst_host.cmd("iperf -s -D")
            time.sleep(1)

            # 源主机发起 TCP 测试
            result = src_host.cmd(f"iperf -c {dst_host.IP()} -t 5")
            full_msg = f"📊 带宽测试结果 ({src} → {dst}):\n{result}"

            # 提取带宽结果（例："[  3]  0.0- 5.0 sec  22.6 GBytes  38.9 Gbits/sec"）
            match = re.search(r"(\d+\.\d+)\s+Gbits/sec", result)
            bw = match.group(0) if match else None

            return full_msg, True, bw

        except Exception as e:
            return f"❌ 带宽测试失败: {e}", False, None


    def _get_host_by_ip(self, ip: str) -> str:
        """根据 IP 查找主机名"""
        net = mm.global_net
        for h in net.hosts:
            if h.IP() == ip:
                return h.name
        return "unknown"


