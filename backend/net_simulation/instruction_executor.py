import json
import time
import traceback

from backend.net_simulation import mininet_manager as mm
from backend.net_simulation.mininet_manager import stop_topology
from backend.net_simulation.ryu_controller import send_flow_mod
from backend.utils.ryu_utils import get_all_switch_ids
from backend.utils.utils import convert_switch_name_to_dpid
from backend.utils.logger import start_new_intent_log, log_intent
from ryu_app.auto_generate_path_intents import build_and_send_all_path_intents

# 初始化协调器（延迟导入 + 单例缓存）
_coordinator = None

def _get_coordinator():
    global _coordinator
    if _coordinator is None:
        from backend.coordinator.coordinator_agent import CoordinatorAgent
        _coordinator = CoordinatorAgent()
    return _coordinator

def execute_instruction(instruction: dict) -> str:
    try:
        coordinator = _get_coordinator()
        instructions = [instruction]
        coordinator.handle_instruction_list(instructions)
        return instructions[0].get("_result", "⚠️ 无执行结果")
    except Exception as e:
        return f"❌ 执行失败: {e}\n{traceback.format_exc()}"

def execute_instruction_list(instruction_list: list[dict]) -> list[str]:
    try:
        coordinator = _get_coordinator()
        coordinator.handle_instruction_list(instruction_list)
        return [instr.get("_result", "⚠️ 无执行结果") for instr in instruction_list]
    except Exception as e:
        return [f"❌ 批量执行失败: {e}\n{traceback.format_exc()}"]
