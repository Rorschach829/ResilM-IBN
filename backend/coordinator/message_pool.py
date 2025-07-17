# backend/coordinator/message_pool.py

import time
import uuid
import json
from datetime import datetime
class MessagePool:
    def __init__(self):
        self.subscribers = []  # 订阅者列表，每个 Agent 都会注册进来

    def subscribe(self, agent):
        if hasattr(agent, "receive"):
            self.subscribers.append(agent)
        else:
            raise ValueError(f"Agent {agent.__class__.__name__} 不支持 receive 方法")

    def publish(self, message: dict, sender: str = "System"):
        """
        将一条 message 广播给所有 agent
        自动补充 sender、timestamp、trace_id 等元信息
        Agent 可选择是否处理该 message
        处理结果由 Agent 在 message 中写入 '_result' 字段（如果有）
        """
        # 注入元信息（若未已有）
        # 信息发起Agent，用于职责追踪
        message.setdefault("sender", sender)

        # 信息发起时间，用于排序/异常检测，精确时间（可用于排序、计算）
        message.setdefault("timestamp", time.time())
        # 作用同上，方便开发者阅读
        message["time_str"] = datetime.fromtimestamp(message["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")

        #信息全局唯一id ，用于追踪一整条意图链、日志串联
        message.setdefault("trace_id", str(uuid.uuid4()))

        print("\n📨 [Message Published]")
        print(json.dumps(message, indent=2, ensure_ascii=False))  # ✅ 多行缩进显示
        print("-" * 50)  # 可选，分隔线

        for agent in self.subscribers:
            try:
                handled = agent.receive(message)
                if handled:
                    break
            except Exception as e:
                print(f"[MessagePool] Agent_Name:{agent.__class__.__name__} 处理异常: {e}")

# 创建全局实例
message_pool = MessagePool()
