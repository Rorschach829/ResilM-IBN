import uuid
import time
from backend.core.message_pool import message_pool

def send_intent(message: dict, sender: str = "CoordinatorAgent"):
    message.setdefault("sender", sender)
    message.setdefault("trace_id", str(uuid.uuid4()))
    message.setdefault("timestamp", int(time.time()))
    message.setdefault("time_str", time.strftime("%Y-%m-%d %H:%M:%S"))
    print(f"[Dispatcher] 📤 向 message_pool 发送消息（action={message.get('action')}）")
    message_pool.publish(message)
