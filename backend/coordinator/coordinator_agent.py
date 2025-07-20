from backend.agents.flow_agent import FlowAgent
from backend.agents.qa_agent import QAAgent
from backend.agents.topology_agent import TopologyAgent
# from backend.agents.planner_agent import PlannerAgent
from backend.coordinator.message_pool import message_pool
from backend.utils.messagepool_utils import send_intent
import uuid, time
from typing import Optional

# 协调型 Agent（负责初始化、统一发布指令）
# 已弃用
class CoordinatorAgent:
    def __init__(self):
        self.name = "CoordinatorAgent"
        print("[CoordinatorAgent] ✅ 初始化完成")

    def handle_instruction_list(self, instructions: list, trace_id: Optional[str] = None) -> list:
        results = []
        trace_id = str(uuid.uuid4())  # ✅ 统一生成 trace_id 给本轮指令
        for instr in instructions:
            send_intent(instr, sender="CoordinatorAgent", trace_id=trace_id)
            result = instr.get("_result", "⚠️ 无结果")
            results.append(result)
        return results
