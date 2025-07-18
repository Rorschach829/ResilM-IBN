# # backend/agents/qa_agent.py
# import time
# from backend.agent_core.qa_manager import QAManager
# from backend.coordinator.message_pool import message_pool

# class QAAgent:
#     def __init__(self):
#         self.manager = QAManager()
        
#     def receive(self, message: dict):
#         action = message.get("action")

#         if action == "ping_test":
#             output, repair_intent = self.manager.ping_test(message)
#             message["_result"] = output
#             if repair_intent:
#                 print("[QAAgent] 发布自动修复流表: %s" % repair_intent)
#                 message_pool.publish(repair_intent,sender="QAAgent")
#             return True

#         elif action == "ping_all":
#             result = self.manager.ping_all()
#             message["_result"] = result
#             return True

#         elif action == "verify_bandwidth":
#             result = self.manager.verify_bandwidth(message)
#             message["_result"] = result
#             return True

#         else:
#             return False

import time
from backend.agent_core.qa_manager import QAManager
from backend.coordinator.message_pool import message_pool

class QAAgent:
    def __init__(self):
        self.manager = QAManager()
        message_pool.subscribe("ping_test", self.handle_ping_test)
        message_pool.subscribe("ping_all", self.handle_ping_all)
        message_pool.subscribe("verify_bandwidth", self.handle_verify_bw)

    def handle_ping_test(self, message: dict):
        output, repair_intent = self.manager.ping_test(message)
        message["_result"] = output
        if repair_intent:
            print("[QAAgent] 发布自动修复流表: %s" % repair_intent)
            message_pool.publish(repair_intent, sender="QAAgent")

    def handle_ping_all(self, message: dict):
        result = self.manager.ping_all()
        message["_result"] = result

    def handle_verify_bw(self, message: dict):
        result = self.manager.verify_bandwidth(message)
        message["_result"] = result

