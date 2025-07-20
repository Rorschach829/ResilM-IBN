from collections import defaultdict
from typing import Callable, Dict, List
import time, uuid, json
class MessagePool:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[dict], None]]] = defaultdict(list)

    def subscribe(self, action: str, callback: Callable[[dict], None]):
        if not callable(callback):
            raise ValueError(f"订阅失败，回调函数 {callback} 不是可调用对象")
        self.subscribers[action].append(callback)
        print(f"[MessagePool] ✅ 已订阅 action: {action} → {callback.__qualname__}")

    def publish(self, message: dict, sender: str):
        # ✅ 注入 sender、时间戳、trace_id
        message["sender"] = sender
        message["timestamp"] = int(time.time())
        message["time_str"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        if "trace_id" not in message:
            message["trace_id"] = str(uuid.uuid4())

        action = message.get("action")
        if not action:
            print("⚠️ 发布失败：消息缺少 action 字段")
            return
        if action not in self.subscribers:
            print(f"⚠️ 无 Agent 订阅 action: {action}，已丢弃")
            return

        print("\n====== 📤 发布新消息到 message_pool ======")
        print(f"Action: {action}")
        print(f"Sender: {sender}")
        print("Message:")
        print(json.dumps(message, indent=2, ensure_ascii=False))
        print("=========================================\n")

        for callback in self.subscribers[action]:
            try:
                callback(message)
            except Exception as e:
                print(f"❌ 执行 action: {action} 回调失败: {e}")


message_pool = MessagePool()
