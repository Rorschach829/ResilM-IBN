import json
import backend.net_simulation.mininet_manager as mm  # ✅ 用模块别名导入
from backend.net_simulation.ryu_controller import send_flow_mod
import requests
from backend.utils.ryu_utils import get_all_switch_ids
from backend.utils.utils import convert_switch_name_to_dpid
from ryu_app.auto_generate_path_intents import build_and_send_all_path_intents
from backend.net_simulation import net_bridge
from backend.utils.logger import start_new_intent_log, log_intent
from backend.net_simulation.mininet_manager import stop_topology
import mininet.log
from contextlib import redirect_stdout
import sys
import time
import re
import os
import io
import traceback
# 引入TopologyAgent
from backend.agents.topology_agent import TopologyAgent
topology_agent = TopologyAgent()

# 引入FlowAgent
from backend.agents.flow_agent import FlowAgent
flow_agent = FlowAgent()

# 在执行link_up的恢复网络操作时，跳过以下actions
SKIP_ACTIONS_ON_RECOVERY = {
    "ping_test",
    "get_flowtable",
    "verify_bandwidth"
}

def convert_switch_name_to_dpid(name: str) -> int:
    """
    将交换机名（如 's1'）转换为对应的 dpid（数字）
    """
    if name.startswith("s"):
        return int(name[1:])
    raise ValueError(f"无法识别的交换机名: {name}")

# 根据LLM输出的不同action进行不同操作
def execute_instruction(instruction: dict) -> str:
    action = instruction.get("action")

    if action == "create_topology":
        return topology_agent.create_topology(instruction)
    elif action == "shutdown_topology":
        return topology_agent.shutdown_topology()
    elif action == "link_down":
        return topology_agent.link_down(instruction)
    elif action == "link_up":
        return topology_agent.link_up(instruction)
    elif action == "install_flowtable":
        return flow_agent.install_flowtable(instruction)
    elif action == "delete_flowtable":
        return flow_agent.delete_flowtable(instruction)
    elif action == "get_flowtable":
        return flow_agent.get_flowtable(instruction)

    elif action == "ping_test":
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
            return f"{src_name} 可以✅ ping 通 {target_host or target_ip}\n{result1}"

        # 等待5秒控制器可能下发流表
        print(f"[PING] 第一次失败，等待 5 秒后重试...")
        time.sleep(5)

        print(f"[PING] 第二次尝试: {src_name} -> {target_ip}")
        result2 = src_host.cmd(f"ping -c 3 -W 1 {target_ip}")
        match2 = re.search(r"(\d+) packets transmitted, (\d+) received", result2)
        success2 = match2 and int(match2.group(2)) >= 1

        return f"{src_name} {'可以✅' if success2 else '无法❌'} ping 通 {target_host or target_ip}\n{result2}"


    elif action == "delete_host":
        if not mm.global_net:
            return "❌ 当前没有拓扑"
        target = instruction.get("target")
        node = mm.global_net.get(target)
        if not node:
            return f"❌ 节点 {target} 不存在"
        mm.global_net.delNode(node)
        return f"✅ 已删除节点 {target}"
    
    # 对主机限速
    elif action == "limit_bandwidth":
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

                # 单向限速（仅 h1 → h2）
                cmds += [
                    f"tc qdisc add dev {dev} root handle 1: htb default 12",
                    f"tc class add dev {dev} parent 1: classid 1:1 htb rate {rate_str}",
                    f"tc filter add dev {dev} protocol ip parent 1: prio 1 u32 match ip dst {dst_ip} flowid 1:1"
                ]
                result = f"✅ 成功设置单向限速：{src} → {dst} 为 {rate}Mbps"
            else:
                # 全局限速（h1 到所有主机都限）
                cmds += [
                    f"tc qdisc add dev {dev} root tbf rate {rate_str} burst 20kb latency 70ms"
                ]
                result = f"✅ 成功设置全局限速：{src} 发往所有主机为 {rate}Mbps"

            for c in cmds:
                src_host.cmd(c)

            return result

        except Exception as e:
            return f"❌ 限速失败: {e}"

    # 对主机测速
    elif action == "verify_bandwidth":
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

    elif action == "clear_bandwidth_limit":
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

            return f"✅ 已取消主机 {host} 的限速设置\n执行结果:\n{result}"
        except Exception as e:
            return f"❌ 取消限速失败: {e}"

    # 测试所有主机连通性
    # 后续可加入结构化输出（JSON），方便前端展示和 agent 分析
    elif action == "ping_all":
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



def wait_for_all_hosts(expected=9, timeout=10):
    import requests
    import time

    for _ in range(timeout):
        try:
            resp = requests.get("http://localhost:8081/intent/valid_hosts")
            if resp.status_code == 200:
                hosts = resp.json()
                print(f"[等待主机] 当前已注册 {len(hosts)} 个主机: {hosts}")
                if len(hosts) >= expected:
                    return True
        except Exception as e:
            print(f"[等待主机] 请求失败: {e}")
        time.sleep(1)
    return False
