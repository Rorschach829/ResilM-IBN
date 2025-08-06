# backend/agents/executor_agent.py

import time
from backend.coordinator.message_pool import message_pool
from backend.utils.logger import record_agent_result

class ExecutorAgent:
    def __init__(self):
        self.name = "ExecutorAgent"
        for action in ["wait", "print", "noop"]:
            message_pool.subscribe(action, self.handle)
        print(f"[ExecutorAgent] ✅ 已注册 wait / print / noop 等通用指令")

    def handle(self, message: dict):
        action = message.get("action")
        if action == "wait":
            duration = message.get("duration", 5)
            print(f"[ExecutorAgent] ⏱️ 正在等待 {duration} 秒...")

            try:
                time.sleep(duration)
                output_msg = f"✅ 已等待 {duration} 秒"
                result_flag = True
            except Exception as e:
                output_msg = f"❌ 等待失败: {e}"
                result_flag = False

            message["_result"] = output_msg

            record_agent_result(
                message=message,
                result=result_flag,
                agent_name="ExecutorAgent",
                extra_info=output_msg,
                value=f"{duration}秒"
            )

        elif action == "print":
            msg = message.get("text", "(空)")
            print(f"[ExecutorAgent][打印]: {msg}")
            message["_result"] = f"🖨️ 已打印: {msg}"
        elif action == "noop":
            print(f"[ExecutorAgent] ⏭️ 收到 noop，占位跳过")
            message["_result"] = "⏭️ 已跳过（noop）"
        else:
            print(f"[ExecutorAgent] ⚠️ 未知指令: {action}")
            message["_result"] = f"❌ 不支持的控制指令: {action}"
