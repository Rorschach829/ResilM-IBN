# coordinator_agent.py
from backend.agents.flow_agent import FlowAgent
from backend.agents.qa_agent import QAAgent
from backend.agents.topology_agent import TopologyAgent
from backend.coordinator.message_pool import MessagePool


class CoordinatorAgent:
    def __init__(self):
        self.message_pool = MessagePool()
        # 初始化并注册各 Agent
        self.agents = {
            "create_topology": TopologyAgent(),
            "install_flowtable": FlowAgent(),
            "delete_flowtable": FlowAgent(),
            "get_flowtable": FlowAgent(),
            "ping_test": QAAgent(),
            "ping_all": QAAgent(),
            "verify_bandwidth": QAAgent(),
            "link_down": TopologyAgent(),
            "link_up": TopologyAgent()
        }
        for agent in self.agents.values():
            self.message_pool.subscribe(agent)

    def handle_instruction_list(self, instructions: list) -> list:
        results = []
        for instr in instructions:
            self.message_pool.publish(instr)
            result = instr.get("_result", "⚠️ 无结果")
            results.append(result)
        return results
