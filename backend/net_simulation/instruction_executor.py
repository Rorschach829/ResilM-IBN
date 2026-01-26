import json
import time
import traceback

from backend.net_simulation import mininet_manager as mm
from backend.net_simulation.mininet_manager import stop_topology
from backend.net_simulation.ryu_controller import send_flow_mod
from backend.utils.ryu_utils import get_all_switch_ids
from backend.utils.utils import convert_switch_name_to_dpid
from backend.utils.logger import log_intent
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

        result = instructions[0].get("_result", "⚠️ 无执行结果")

        # ✅ 添加日志记录
        log_intent(
            intent_text=instruction.get("intent_text", "(未提供原始意图)"),
            instruction=instruction,
            result=result
        )

        return result

    except Exception as e:
        error_msg = f"❌ 执行失败: {e}\n{traceback.format_exc()}"
        # ✅ 失败也写日志
        log_intent(
            intent_text=instruction.get("intent_text", "(未提供原始意图)"),
            instruction=instruction,
            result=error_msg
        )
        return error_msg


def execute_instruction_list(instruction_list: list[dict]) -> list[str]:
    try:
        coordinator = _get_coordinator()
        coordinator.handle_instruction_list(instruction_list)

        results = []
        for instr in instruction_list:
            result = instr.get("_result", "⚠️ 无执行结果")
            results.append(result)

            # ✅ 每条指令单独记录日志
            log_intent(
                intent_text=instr.get("intent_text", "(未提供原始意图)"),
                instruction=instr,
                result=result
            )

        return results

    except Exception as e:
        error_msg = f"❌ 批量执行失败: {e}\n{traceback.format_exc()}"
        # ✅ 批量失败，全部写成失败记录
        for instr in instruction_list:
            log_intent(
                intent_text=instr.get("intent_text", "(未提供原始意图)"),
                instruction=instr,
                result=error_msg
            )
        return [error_msg for _ in instruction_list]

