from backend.agent_core.topology_manager import TopologyManager

class TopologyAgent:
    def __init__(self):
        self.manager = TopologyManager()

    def receive(self, message: dict) -> bool:
        action = message.get("action")

        if action == "create_topology":
            result = self.manager.create_topology(message)
            message["_result"] = result
            return True

        elif action == "link_down":
            result = self.manager.link_down(message)
            message["_result"] = result
            return True

        elif action == "link_up":
            result = self.manager.link_up(message)
            message["_result"] = result
            return True

        return False
        
    
