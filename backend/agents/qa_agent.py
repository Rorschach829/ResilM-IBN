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
        output_msg, repair_intent, success = self.manager.ping_test(message)
        message["_result"] = output_msg  # 保留控制台提示

        if repair_intent:
            print("[QAAgent] 发布自动修复流表: %s" % repair_intent)
            trace_id = message.get("trace_id")
            repair_intent["triggered_by"] = message.get("sender", "Unknown")
            send_intent(repair_intent, sender="QAAgent", trace_id=trace_id)

        record_agent_result(
            message=message,
            result=success,
            agent_name="QAAgent",
            extra_info=output_msg,
            value="ping success" if success else "ping failed"
        )


    def handle_ping_all(self, message: dict):
        msg, is_result_ok, value = self.manager.ping_all(message)
        message["_result"] = msg

        record_agent_result(
            message=message,
            result=is_result_ok,  # ✅ 只要验证结果和预期一致，就算成功
            agent_name="QAAgent",
            extra_info=msg,
            value=f"{value} failed pairs" if not is_result_ok else f"{value} pairs verified"
        )


    def handle_verify_bw(self, message: dict):
        result = self.manager.verify_bandwidth(message)
        message["_result"] = result
        record_agent_result(message, result, "QAAgent")

    def handle_verify_bw(self, message: dict):
        output_msg, success, bandwidth = self.manager.verify_bandwidth(message)
        message["_result"] = output_msg

        record_agent_result(
            message=message,
            result=success,
            agent_name="QAAgent",
            extra_info=output_msg,
            value=bandwidth  # e.g. "38.9 Gbits/sec"
        )


