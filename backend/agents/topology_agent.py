from backend.coordinator.message_pool import message_pool
from backend.agent_core.topology_manager import TopologyManager
from backend.utils.logger import record_agent_result
class TopologyAgent:
    def __init__(self):
        self.manager = TopologyManager()
        message_pool.subscribe("create_topology", self.handle_create)
        message_pool.subscribe("link_down", self.handle_link_down)
        message_pool.subscribe("link_up", self.handle_link_up)
        
    def handle_create(self, message: dict):
        success, msg, host_count = self.manager.create_topology(message)
        message["_result"] = msg
        record_agent_result(
            message=message,
            result=success,
            agent_name="TopologyAgent",
            extra_info=msg,
            value=f"{host_count} hosts"
        )

    def handle_link_down(self, message: dict):
        success, msg = self.manager.link_down(message)
        message["_result"] = msg
        record_agent_result(
            message=message,
            result=success,
            agent_name="TopologyAgent",
            extra_info=msg
        )

    def handle_link_up(self, message: dict):
        success, msg = self.manager.link_up(message)
        message["_result"] = msg
        record_agent_result(
            message=message,
            result=success,
            agent_name="TopologyAgent",
            extra_info=msg
        )

