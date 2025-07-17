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
from backend.coordinator.coordinator_agent import CoordinatorAgent
import mininet.log
from contextlib import redirect_stdout
import sys
import time
import re
import os
import io
import traceback
coordinator = CoordinatorAgent()
# 引入TopologyAgent
from backend.agents.topology_agent import TopologyAgent
topology_agent = TopologyAgent()

# 引入FlowAgent
from backend.agents.flow_agent import FlowAgent
flow_agent = FlowAgent()

# 引入QA Agent
from backend.agents.qa_agent import QAAgent
qa_agent = QAAgent()


# 初始化协调器，只初始化一次

def execute_instruction(instruction: dict) -> str:
    instructions = [instruction]
    coordinator.handle_instruction_list(instructions)
    return instructions[0].get("_result", "⚠️ 无执行结果")

def execute_instruction_list(instruction_list: list[dict]) -> list[str]:
    coordinator.handle_instruction_list(instruction_list)
    return [instr.get("_result", "⚠️ 无结果") for instr in instruction_list]
