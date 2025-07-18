# import time
# import uuid
# from backend.llm.llm_utils import call_llm_for_planning
# from backend.coordinator.message_pool import message_pool

# class PlannerAgent:
#     def __init__(self):
#         self.name = "PlannerAgent"
#         message_pool.subscribe("plan", self.handle_plan)
#         print("[PlannerAgent] ✅ 已注册，监听 action='plan' 消息")

#     def handle_plan(self, message):
#         intent_text = message.get("intent_text", "")
#         trace_id = message.get("trace_id", str(uuid.uuid4()))
#         print(f"[PlannerAgent] 接收到意图文本: {intent_text}")

#         try:
#             # 使用 LLM 解析意图为任务列表
#             tasks = call_llm_for_planning(intent_text)
#         except Exception as e:
#             print(f"[PlannerAgent] ❌ 调用 LLM 失败: {e}")
#             return

#         # 注入公共字段并广播
#         for task in tasks:
#             task["sender"] = self.name
#             task["timestamp"] = int(time.time())
#             task["time_str"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
#             task["trace_id"] = trace_id
#             message_pool.publish(task)
from backend.coordinator.message_pool import message_pool
from backend.llm.llm_utils import call_llm_for_planning
import time, uuid

class PlannerAgent:
    def __init__(self):
        self.name = "PlannerAgent"
        message_pool.subscribe("plan", self.handle_plan)

    def handle_plan(self, message: dict):
        intent_text = message.get("intent_text", "")
        trace_id = message.get("trace_id", str(uuid.uuid4()))
        print(f"[PlannerAgent] 收到意图: {intent_text}")

        try:
            tasks = call_llm_for_planning(intent_text)
        except Exception as e:
            print(f"[PlannerAgent] ❌ LLM 任务拆解失败: {e}")
            return

        for task in tasks:
            task["sender"] = self.name
            task["trace_id"] = trace_id
            task["timestamp"] = int(time.time())
            task["time_str"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            message_pool.publish(task)
