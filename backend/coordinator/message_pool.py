# # backend/coordinator/message_pool.py

# import time
# import uuid
# import json
# from datetime import datetime
# class MessagePool:
#     def __init__(self):
#         self.subscribers = []  # 订阅者列表，每个 Agent 都会注册进来

#     def subscribe(self, agent):
#         if hasattr(agent, "receive"):
#             self.subscribers.append(agent)
#         else:
#             raise ValueError(f"Agent {agent.__class__.__name__} 不支持 receive 方法")

#     def publish(self, message: dict, sender: str = "System"):
#         """
#         将一条 message 广播给所有 agent
#         自动补充 sender、timestamp、trace_id 等元信息
#         Agent 可选择是否处理该 message
#         处理结果由 Agent 在 message 中写入 '_result' 字段（如果有）
#         """
#         # 注入元信息（若未已有）
#         # 信息发起Agent，用于职责追踪
#         message.setdefault("sender", sender)

#         # 信息发起时间，用于排序/异常检测，精确时间（可用于排序、计算）
#         message.setdefault("timestamp", time.time())
#         # 作用同上，方便开发者阅读
#         message["time_str"] = datetime.fromtimestamp(message["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")

#         #信息全局唯一id ，用于追踪一整条意图链、日志串联
#         message.setdefault("trace_id", str(uuid.uuid4()))

#         print("\n📨 [Message Published]")
#         print(json.dumps(message, indent=2, ensure_ascii=False))  # ✅ 多行缩进显示
#         print("-" * 50)  # 可选，分隔线

#         for agent in self.subscribers:
#             try:
#                 handled = agent.receive(message)
#                 if handled:
#                     break
#             except Exception as e:
#                 print(f"[MessagePool] Agent_Name:{agent.__class__.__name__} 处理异常: {e}")

# # 创建全局实例
# message_pool = MessagePool()

from collections import defaultdict
from typing import Callable, Dict, List
import time, uuid
class MessagePool:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[dict], None]]] = defaultdict(list)

    def subscribe(self, action: str, callback: Callable[[dict], None]):
        if not callable(callback):
            raise ValueError(f"订阅失败，回调函数 {callback} 不是可调用对象")
        self.subscribers[action].append(callback)
        print(f"[MessagePool] ✅ 已订阅 action: {action} → {callback.__qualname__}")

    def publish(self, message: dict, sender: str = "Unknown"):
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

        for callback in self.subscribers[action]:
            try:
                callback(message)
            except Exception as e:
                print(f"❌ 执行 action: {action} 回调失败: {e}")


message_pool = MessagePool()
