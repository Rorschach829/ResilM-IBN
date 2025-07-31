import time
from backend.agent_core.qa_manager import QAManager
from backend.coordinator.message_pool import message_pool
from backend.utils.messagepool_utils import send_intent
from backend.utils.logger import record_agent_result

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
            trace_id = message.get("trace_id")  # ⬅️ 拿到原始 ping_test 指令的 trace_id
            repair_intent["triggered_by"] = message.get("sender", "Unknown")
            send_intent(repair_intent, sender="QAAgent", trace_id=trace_id)

        record_agent_result(message, output, "QAAgent")

    def handle_ping_all(self, message: dict):
        result = self.manager.ping_all()
        message["_result"] = result
        record_agent_result(message, result, "QAAgent")

    def handle_verify_bw(self, message: dict):
        result = self.manager.verify_bandwidth(message)
        message["_result"] = result
        record_agent_result(message, result, "QAAgent")

