# backend/agents/flow_agent.py (重构版，支持消息池通信)
from backend.agent_core.flowtable_manager import FlowTableManager

class FlowAgent:
    def __init__(self):
        self.manager = FlowTableManager()

    def receive(self, message: dict):
        action = message.get("action")
        
        if action == "install_flowtable":
            result = self.manager.install_rule(message)
            message["_result"] = result
            return True

        elif action == "delete_flowtable":
            result = self.manager.delete_rule(message)
            message["_result"] = result
            return True

        elif action == "get_flowtable":
            result = self.manager.query_table(message)
            message["_result"] = result
            return True

        elif action == "limit_bandwidth":
            result = self.manager.limit_bandwidth(message)
            message["_result"] = result
            return True

        elif action == "clear_bandwidth_limit":
            result = self.manager.clear_bandwidth_limit(message)
            message["_result"] = result
            return True

        else:
            return False  # 不处理该消息
