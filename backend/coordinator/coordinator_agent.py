# # coordinator_agent.py
# from backend.agents.flow_agent import FlowAgent
# from backend.agents.qa_agent import QAAgent
# from backend.agents.topology_agent import TopologyAgent
# from backend.agents.planner_agent import PlannerAgent
# from backend.coordinator.message_pool import message_pool

# # 协调型Agent
# class CoordinatorAgent:
#     def __init__(self):
#         self.message_pool = message_pool
#         # 初始化并注册各 Agent
#         self.agents = {
#             "create_topology": TopologyAgent(),
#             "install_flowtable": FlowAgent(),
#             "delete_flowtable": FlowAgent(),
#             "get_flowtable": FlowAgent(),
#             "ping_test": QAAgent(),
#             "ping_all": QAAgent(),
#             "verify_bandwidth": QAAgent(),
#             "link_down": TopologyAgent(),
#             "link_up": TopologyAgent()
#         }
#         for agent in self.agents.values():
#             self.message_pool.subscribe(agent)

#         # ✅ 单独注册 规划型Agent:PlannerAgent
#         self.planner_agent = PlannerAgent()
#         self.message_pool.subscribe(self.planner_agent)


#     def handle_instruction_list(self, instructions: list) -> list:
#         results = []
#         for instr in instructions:
#             self.message_pool.publish(instr,sender="CoordinatorAgent")
#             result = instr.get("_result", "⚠️ 无结果")
#             results.append(result)
#         return results

from backend.agents.flow_agent import FlowAgent
from backend.agents.qa_agent import QAAgent
from backend.agents.topology_agent import TopologyAgent
from backend.agents.planner_agent import PlannerAgent
from backend.coordinator.message_pool import message_pool

# 协调型 Agent（负责初始化、统一发布指令）
class CoordinatorAgent:
    def __init__(self):
        # 初始化所有 Agent（它们自己注册自己支持的 action）
        self.flow_agent = FlowAgent()
        self.qa_agent = QAAgent()
        self.topo_agent = TopologyAgent()
        self.planner_agent = PlannerAgent()

        print("[CoordinatorAgent] ✅ 所有 Agent 已初始化")

    def handle_instruction_list(self, instructions: list) -> list:
        results = []
        for instr in instructions:
            message_pool.publish(instr, sender="CoordinatorAgent")
            result = instr.get("_result", "⚠️ 无结果")
            results.append(result)
        return results
