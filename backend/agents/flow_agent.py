from backend.coordinator.message_pool import message_pool
from backend.agent_core.flowtable_manager import FlowTableManager
from backend.utils.logger import record_agent_result
from backend.utils.messagepool_utils import send_intent
from backend.controller.controller_instance import get_controller_instance
from ryu.lib import hub
import time
class FlowAgent:
    def __init__(self):
        self.manager = FlowTableManager()
        message_pool.subscribe("install_flowtable", self.handle_install)
        message_pool.subscribe("delete_flowtable", self.handle_delete)
        message_pool.subscribe("get_flowtable", self.handle_get)
        message_pool.subscribe("limit_bandwidth", self.handle_limit_bw)
        message_pool.subscribe("clear_bandwidth_limit", self.handle_clear_bw)
        message_pool.subscribe("repair_suggestion", self.handle_repair_suggestion)
    
    def handle_install(self, message: dict):
        if "triggered_by" in message:
            print(f"[FlowAgent] 接收到 QAAgent 自动修复意图: {message['triggered_by']}")
            message["_source_agent"] = "QAAgent"
        else:
            message["_source_agent"] = "User"

        output_msg, result_flag, count = self.manager.install_rule(message)
        message["_result"] = output_msg

        record_agent_result(
            message=message,
            result=result_flag,
            agent_name="FlowAgent",
            extra_info=output_msg,
            value=f"{count}/{len(message.get('switches', []))} switches OK"
        )

    def handle_delete(self, message: dict):
        output_msg, result_flag, count = self.manager.delete_rule(message)
        message["_result"] = output_msg

        record_agent_result(
            message=message,
            result=result_flag,
            agent_name="FlowAgent",
            extra_info=output_msg,
            value=f"{count} rules deleted" if count is not None else None
        )


    def handle_get(self, message: dict):
        output_msg, result_flag, count = self.manager.query_table(message)
        message["_result"] = output_msg

        record_agent_result(
            message=message,
            result=result_flag,
            agent_name="FlowAgent",
            extra_info=output_msg,
            value=f"{count}/{len(message.get('switches', []))} switches OK" if count is not None else None
        )


    def handle_limit_bw(self, message: dict):
        output_msg, result_flag, value_str = self.manager.limit_bandwidth(message)
        message["_result"] = output_msg

        record_agent_result(
            message=message,
            result=result_flag,
            agent_name="FlowAgent",
            extra_info=output_msg,
            value=value_str
        )


    def handle_clear_bw(self, message: dict):
        output_msg, result_flag, value_host = self.manager.clear_bandwidth_limit(message)
        message["_result"] = output_msg

        record_agent_result(
            message=message,
            result=result_flag,
            agent_name="FlowAgent",
            extra_info=output_msg,
            value=value_host  # 可选字段，记录取消限速的主机名
        )

    def handle_repair_suggestion(self, message: dict):
        if not message.get("auto_fix", False):
            print("[FlowAgent] ❌ 未授权自动修复，忽略 repair_suggestion")
            return

        print("[FlowAgent] ✅ 接收到 QAAgent 的修复建议，准备执行修复操作")

        switches = message.get("switches", [])
        match = message.get("match", {})
        trace_id = message.get("trace_id")

        # 记录一下建议来源
        reason = message.get("reason", "unspecified")
        print(f"[FlowAgent] 修复建议说明: {reason}")

        # 发送 delete_flowtable 指令（清空相关交换机）
        delete_msg = {
            "action": "delete_flowtable",
            "switches": switches,
            "match": match
        }
        send_intent(delete_msg, sender="FlowAgent", trace_id=trace_id)

        time.sleep(1)  # 等待删除完成

        # ===== 尝试使用 controller 重建完整路径流表 =====
        try:
            
            controller = get_controller_instance()
            if controller is None:
                raise RuntimeError("controller instance is None")

            src_ip = match["nw_src"]
            dst_ip = match["nw_dst"]

            src_mac = controller.get_mac_from_ip(src_ip)
            dst_mac = controller.get_mac_from_ip(dst_ip)

            print(f"[FlowAgent] 🛠 调用 controller 安装路径：{src_mac} -> {dst_mac}")
            hub.spawn(controller.install_path_between_hosts, src_mac, dst_mac)
            hub.spawn(controller.install_path_between_hosts, dst_mac, src_mac)

            # controller.install_path_between_hosts(src_mac, dst_mac)
            # controller.install_path_between_hosts(dst_mac, src_mac)

            print(f"[FlowAgent] ✅ repair_suggestion 已使用 controller 自动安装双向路径流表")

            record_agent_result(
                message=message,
                result=True,
                agent_name="FlowAgent",
                extra_info="✅ 已调用 controller.install_path_between_hosts 双向修复",
                value="repair_suggestion"
            )
            return

        except Exception as e:
            print(f"[FlowAgent] ⚠️ 无法使用 controller 修复路径，原因: {e}")
            print(f"[FlowAgent] 🚧 fallback 回原 install_flowtable 方式")

        # ===== fallback: 原始方式安装 ALLOW 流表 =====
        install_msg = {
            "action": "install_flowtable",
            "switches": switches,
            "extra": {
                "match": match,
                "actions": "ALLOW",
                "priority": 100
            },
            "triggered_by": {
                "agent": "QAAgent",
                "reason": reason
            }
        }
        send_intent(install_msg, sender="FlowAgent", trace_id=trace_id)

        print(f"[FlowAgent] ✅ delete + install 指令已转发至消息池")

        record_agent_result(
            message=message,
            result=True,
            agent_name="FlowAgent",
            extra_info="✅ fallback 使用 install_flowtable 安装放行流表",
            value="repair_suggestion"
        )

    # def handle_repair_suggestion(self, message: dict):
    #     if not message.get("auto_fix", False):
    #         print("[FlowAgent] ❌ 未授权自动修复，忽略 repair_suggestion")
    #         return

    #     print("[FlowAgent] ✅ 接收到 QAAgent 的修复建议，准备执行修复操作")

    #     switches = message.get("switches", [])
    #     match = message.get("match", {})
    #     trace_id = message.get("trace_id")

    #     # 记录一下建议来源
    #     reason = message.get("reason", "unspecified")
    #     print(f"[FlowAgent] 修复建议说明: {reason}")

    #     # 发送 delete_flowtable 指令（清空相关交换机）
    #     delete_msg = {
    #         "action": "delete_flowtable",
    #         "switches": switches,
    #         "match": match
    #     }
    #     send_intent(delete_msg, sender="FlowAgent", trace_id=trace_id)

    #     # 等待 1 秒，避免删除未完成
    #     time.sleep(1)

    #     # 发送 install_flowtable 指令（重新安装允许规则）
    #     install_msg = {
    #         "action": "install_flowtable",
    #         "switches": switches,
    #         "extra": {
    #             "match": match,
    #             "actions": "ALLOW",
    #             "priority": 100
    #         },
    #         "triggered_by": {
    #             "agent": "QAAgent",
    #             "reason": reason
    #         }
    #     }
    #     send_intent(install_msg, sender="FlowAgent", trace_id=trace_id)

    #     print(f"[FlowAgent] ✅ delete + install 指令已转发至消息池")
        
    #     record_agent_result(
    #         message=message,
    #         result=True,
    #         agent_name="FlowAgent",
    #         extra_info="✅ 已根据 QAAgent 建议执行 delete + install 操作",
    #         value="repair_suggestion"
    #     )

