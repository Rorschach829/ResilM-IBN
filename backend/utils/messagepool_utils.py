import uuid
import time
from backend.coordinator.message_pool import message_pool

# def send_intent(message: dict, sender: str = "CoordinatorAgent", trace_id: str = None):
#     message.setdefault("sender", sender)
#     message.setdefault("trace_id", trace_id or str(uuid.uuid4()))
#     message.setdefault("timestamp", int(time.time()))
#     message.setdefault("time_str", time.strftime("%Y-%m-%d %H:%M:%S"))
#     print(f"[{sender}] 📤 向 message_pool 发送消息（action={message.get('action')}）")
#     message_pool.publish(message)

def send_intent(message: dict, sender: str = "GJW", trace_id: str = None):
    message["sender"] = sender  # ✅ 强制设置，不用 setdefault
    message["trace_id"] = trace_id or str(uuid.uuid4())
    message["timestamp"] = int(time.time())
    message["time_str"] = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{sender}] 📤 向 message_pool 发送消息（action={message.get('action')}）")
    message_pool.publish(message,sender = sender)


