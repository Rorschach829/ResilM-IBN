import re
from backend.net_simulation import mininet_manager as mm
from backend.agents.flow_agent import FlowAgent
from backend.utils.utils import convert_switch_name_to_dpid
import time
# 只做检验操作，不做修改操作
class QAAgent:
    def __init__(self):
        self.flow_agent = FlowAgent()

    def validate_ping(self, src: str, target_ip: str) -> bool:
        """
        执行 ping 操作，判断是否通畅
        """
        if not mm.global_net:
            print("[QA] 当前没有拓扑")
            return False

        src_host = mm.global_net.get(src)
        if not src_host:
            print(f"[QA] 主机 {src} 不存在")
            return False

        result = src_host.cmd(f"ping -c 3 -W 1 {target_ip}")
        print(f"[QA] ping 结果:\n{result}")

        match = re.search(r"(\d+) packets transmitted, (\d+) received", result)
        return bool(match and int(match.group(2)) >= 1)

    def validate_all_connectivity(self) -> dict:
        """
        测试所有主机之间是否连通，返回失败对列表
        """
        from backend.utils.topology_utils import robust_ping_pairs_multi_thread

        if not mm.global_net:
            return {"error": "❌ 当前没有拓扑"}

        result = robust_ping_pairs_multi_thread(mm.global_net)
        return result

    def validate_bandwidth(self, src: str, dst: str, duration: int = 5) -> float:
        if not mm.global_net:
            return 0.0

        src_host = mm.global_net.get(src)
        dst_host = mm.global_net.get(dst)

        if not src_host or not dst_host:
            return 0.0

        # 启动目标主机上的 iperf server
        dst_host.cmd("killall -9 iperf")
        dst_host.cmd("iperf -s -D")

        # 在源主机上运行 iperf client
        time.sleep(0.5)
        result = src_host.cmd(f"iperf -c {dst_host.IP()} -t {duration}")
        print("[QA] 带宽测试结果:\n" + result)

        try:
            # 匹配 Mbps 或 Gbps 的结果
            match = re.findall(r"([\d.]+)\s+(M|G)bits/sec", result)
            if match:
                val, unit = match[-1]  # 取最后一行的数值
                val = float(val)
                if unit == "G":
                    val *= 1000
                return val
            else:
                print("[QA] ❌ 无法提取带宽")
                return 0.0
        except Exception as e:
            print(f"[QA] ❌ 解析带宽失败: {e}")
            return 0.0


    def validate_flow_installed(self, switch: str, match_rule: dict) -> bool:
        """
        判断流表中是否存在指定规则
        """
        instruction = {"switches": [switch]}
        result = self.flow_agent.get_flowtable(instruction)

        return json.dumps(match_rule, sort_keys=True) in result
