# # backend/agents/flow_agent.py (重构版，支持消息池通信)
# from backend.agent_core.flowtable_manager import FlowTableManager

# class FlowAgent:
#     def __init__(self):
#         self.manager = FlowTableManager()

#     def receive(self, message: dict):
#         action = message.get("action")
        
#         if action == "install_flowtable":
#             if "triggered_by" in message:
#                 print(f"[FlowAgent] 接收到 QAAgent 自动修复意图: {message['triggered_by']}")
#                 message["_source_agent"] = "QAAgent"
#             else:
#                 message["_source_agent"] = "User"

#             result = self.manager.install_rule(message)
#             message["_result"] = result
#             return True

#         elif action == "delete_flowtable":
#             result = self.manager.delete_rule(message)
#             message["_result"] = result
#             return True

#         elif action == "get_flowtable":
#             result = self.manager.query_table(message)
#             message["_result"] = result
#             return True

#         elif action == "limit_bandwidth":
#             result = self.manager.limit_bandwidth(message)
#             message["_result"] = result
#             return True

#         elif action == "clear_bandwidth_limit":
#             result = self.manager.clear_bandwidth_limit(message)
#             message["_result"] = result
#             return True

#         else:
#             return False  # 不处理该消息
from backend.coordinator.message_pool import message_pool
from backend.agent_core.flowtable_manager import FlowTableManager

class FlowAgent:
    def __init__(self):
        self.manager = FlowTableManager()
        message_pool.subscribe("install_flowtable", self.handle_install)
        message_pool.subscribe("delete_flowtable", self.handle_delete)
        message_pool.subscribe("get_flowtable", self.handle_get)
        message_pool.subscribe("limit_bandwidth", self.handle_limit_bw)
        message_pool.subscribe("clear_bandwidth_limit", self.handle_clear_bw)

    def handle_install(self, message: dict):
        if "triggered_by" in message:
            print(f"[FlowAgent] 接收到 QAAgent 自动修复意图: {message['triggered_by']}")
            message["_source_agent"] = "QAAgent"
        else:
            message["_source_agent"] = "User"

        result = self.manager.install_rule(message)
        message["_result"] = result

    def handle_delete(self, message: dict):
        result = self.manager.delete_rule(message)
        message["_result"] = result

    def handle_get(self, message: dict):
        result = self.manager.query_table(message)
        message["_result"] = result

    def handle_limit_bw(self, message: dict):
        result = self.manager.limit_bandwidth(message)
        message["_result"] = result

    def handle_clear_bw(self, message: dict):
        result = self.manager.clear_bandwidth_limit(message)
        message["_result"] = result
