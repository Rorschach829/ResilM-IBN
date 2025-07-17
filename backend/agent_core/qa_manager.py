# backend/agent_core/qa_manager.py
import time
from backend.net_simulation import mininet_manager as mm
import re
class QAManager:
    def ping_test(self, instruction: dict) -> tuple[str, dict or None]:
        """返回测试结果和失败信息（如果有）"""
        print(f"[DEBUG] global_net状态: {mm.global_net}")
        if not mm.global_net:
            return "❌ 当前没有拓扑 (请先创建拓扑或检查global_net引用)"

        src_name = instruction.get("extra", {}).get("source") or instruction.get("source")
        target_ip = instruction.get("extra", {}).get("target") or instruction.get("target")
        target_host = instruction.get("extra", {}).get("target_host") or instruction.get("target")

        if not src_name or not target_ip:
            return "❌ 指令缺少 source 或 target"

        src_host = mm.global_net.get(src_name)
        if not src_host:
            return f"❌ 主机 {src_name} 不存在"

        # 发送3个包，有一个包收到了就说明Ping通了
        print(f"[PING] 第一次尝试: {src_name} -> {target_ip}")
        result1 = src_host.cmd(f"ping -c 3 -W 1 {target_ip}")
        match1 = re.search(r"(\d+) packets transmitted, (\d+) received", result1)
        success1 = match1 and int(match1.group(2)) >= 1

        if success1:
            return f"{src_name} 可以✅ ping 通 {target_host or target_ip}\n{result1}", None

        # 等待5秒控制器可能下发流表
        print(f"[PING] 第一次失败，等待 5 秒后重试...")
        time.sleep(5)

        print(f"[PING] 第二次尝试: {src_name} -> {target_ip}")
        result2 = src_host.cmd(f"ping -c 3 -W 1 {target_ip}")
        match2 = re.search(r"(\d+) packets transmitted, (\d+) received", result2)
        success2 = match2 and int(match2.group(2)) >= 1

        return f"{src_name} {'可以✅' if success2 else '无法❌'} ping 通 {target_host or target_ip}\n{result2}"


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
