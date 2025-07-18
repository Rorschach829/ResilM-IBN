# from backend.agent_core.topology_manager import TopologyManager

# class TopologyAgent:
#     def __init__(self):
#         self.manager = TopologyManager()

#     def receive(self, message: dict) -> bool:
#         action = message.get("action")

#         if action == "create_topology":
#             result = self.manager.create_topology(message)
#             message["_result"] = result
#             return True

#         elif action == "link_down":
#             result = self.manager.link_down(message)
#             message["_result"] = result
#             return True

#         elif action == "link_up":
#             result = self.manager.link_up(message)
#             message["_result"] = result
#             return True

#         return False
        
from backend.coordinator.message_pool import message_pool
from backend.agent_core.topology_manager import TopologyManager

class TopologyAgent:
    def __init__(self):
        self.manager = TopologyManager()
        message_pool.subscribe("create_topology", self.handle_create)
        message_pool.subscribe("link_down", self.handle_link_down)
        message_pool.subscribe("link_up", self.handle_link_up)

    def handle_create(self, message: dict):
        result = self.manager.create_topology(message)
        message["_result"] = result

    def handle_link_down(self, message: dict):
        result = self.manager.link_down(message)
        message["_result"] = result

    def handle_link_up(self, message: dict):
        result = self.manager.link_up(message)
        message["_result"] = result
   
