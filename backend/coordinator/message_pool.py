# 消息池
class MessagePool:
    def __init__(self):
        self.subscribers = []  # 订阅者列表，每个 Agent 都会注册进来

    def subscribe(self, agent):
        if hasattr(agent, "receive"):
            self.subscribers.append(agent)
        else:
            raise ValueError(f"Agent {agent.__class__.__name__} 不支持 receive 方法")

    def publish(self, message: dict):
        """
        将一条 message 广播给所有 agent
        Agent 可选择是否处理该 message
        处理结果由 Agent 在 message 中写入 '_result' 字段（如果有）
        """
        for agent in self.subscribers:
            try:
                handled = agent.receive(message)  # 支持 None/False 表示未处理
                if handled:
                    break  # 一旦有 agent 成功处理，就不继续广播
            except Exception as e:
                print(f"[MessagePool] Agent_Name:{agent.__class__.__name__} 处理异常: {e}")

message_pool = MessagePool()