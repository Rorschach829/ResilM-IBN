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

# 引入QA Agent
from backend.agents.qa_agent import QAAgent
qa_agent = QAAgent()


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
        src = instruction.get("extra", {}).get("source") or instruction.get("source")
        ip = instruction.get("extra", {}).get("target") or instruction.get("target")
        name = instruction.get("extra", {}).get("target_host") or ip
        if not src or not ip:
            return "❌ 缺参数"
        return f"{src} {'✅可达' if qa_agent.validate_ping(src, ip) else '❌不可达'} {name}"

    elif action == "ping_all":
        res = qa_agent.validate_all_connectivity()
        if "error" in res:
            return res["error"]
        
        failed = res["failed_pairs"]
        if not failed:
            return f"✅ 所有主机互通（共 {res['total']} 对）"
        
        summary = f"❌ 无法通信对：{len(failed)} 对\n" + "\n".join(f"- {s} → {d}" for s, d in failed)
        return summary + f"\n✅ 其余正常：{res['success']} 对"


# 对主机限速
    elif action == "limit_bandwidth":
        return flow_agent.limit_bandwidth(instruction)
# 清除限速规则
    elif action == "clear_bandwidth_limit":
        return flow_agent.clear_bandwidth_limit(instruction)


    # 对主机测速
    elif action == "verify_bandwidth":
        src = instruction.get("src_host")
        dst = instruction.get("dst_host")

        if not src or not dst:
            return "❌ 缺少主机名"

        bandwidth = qa_agent.validate_bandwidth(src, dst)
        if bandwidth <= 0:
            return f"❌ 带宽测试失败：{src} → {dst}"
        return f"📊 带宽测试结果：{src} → {dst} = {bandwidth:.2f} Mbps"



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
