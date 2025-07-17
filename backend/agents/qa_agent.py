# backend/agents/qa_agent.py
import time
from backend.agent_core.qa_manager import QAManager
from backend.coordinator.message_pool import message_pool

class QAAgent:
    def __init__(self):
        self.manager = QAManager()
        
    def receive(self, message: dict):
        action = message.get("action")

        if action == "ping_test":
            output, repair_intent = self.manager.ping_test(message)
            message["_result"] = output
            if repair_intent:
                print("[QAAgent] 发布自动修复流表: %s" % repair_intent)
                message_pool.publish(repair_intent)
            return True

        elif action == "ping_all":
            result = self.manager.ping_all()
            message["_result"] = result
            return True

        elif action == "verify_bandwidth":
            result = self.manager.verify_bandwidth(message)
            message["_result"] = result
            return True

        else:
            return False

    def construct_fix_flow(self, info: dict) -> dict:
        """构造修复流表的指令"""
        print("🔧 QAAgent 发现 ping 失败，准备自动触发 FlowAgent 修复")
        src = info["src"]
        dst = info["dst"]
        dst_ip = info["dst_ip"]

        return {
            "action": "install_flowtable",
            "switches": ["s1"],  # 你可以根据拓扑智能指定
            "extra": {
                "match": {
                    "eth_type": 2048,
                    "ipv4_src": src,
                    "ipv4_dst": dst_ip,
                    "ip_proto": 1
                },
                "actions": "ALLOW",
                "priority": 100
            },
            "_from": "qa_agent",
            "_timestamp": time.time()
        }
