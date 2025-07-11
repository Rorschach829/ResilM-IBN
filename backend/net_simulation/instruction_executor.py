import json
import backend.net_simulation.mininet_manager as mm  # ✅ 用模块别名导入
from backend.net_simulation.ryu_controller import send_flow_mod
import requests
from backend.utils.ryu_utils import get_all_switch_ids


def execute_instruction(instruction: dict) -> str:
    action = instruction.get("action")

    if action == "create_topology":
        result = mm.rebuild_topology(instruction)
        print(f"[DEBUG] 拓扑创建结果: {result}")
        return result

    elif action == "install_flowtable":
        flow_rule = {
            "dpid": 1,  # 默认交换机ID，可扩展支持多个
            "match": instruction.get("extra", {}).get("match", {}),
            "actions": [],  # DENY 默认丢弃
            "priority": instruction.get("extra", {}).get("priority", 100)
        }

        if instruction.get("extra", {}).get("actions") == "DENY":
            if send_flow_mod(flow_rule):
                return f"✅ 流表下发成功 (阻断 {flow_rule['match']})"
            else:
                return "❌ 流表下发失败"

    elif action == "ping_test":
        print(f"[DEBUG] global_net状态: {mm.global_net}")
        if not mm.global_net:
            return "❌ 当前没有拓扑 (请先创建拓扑或检查global_net引用)"

        # ✅ 双保险：先取 extra 里的，没有再取外层的
        src_name = instruction.get("extra", {}).get("source") or instruction.get("source")
        target_ip = instruction.get("extra", {}).get("target") or instruction.get("target")
        target_host = instruction.get("extra", {}).get("target_host") or instruction.get("target")

        if not src_name or not target_ip:
            return "❌ 指令缺少 source 或 target"

        src_host = mm.global_net.get(src_name)

        if not src_host:
            return f"❌ 主机 {src_name} 不存在"

        # 此处使用 IP 执行 ping，而不是主机名
        result = src_host.cmd(f"ping -c 3 {target_ip}")
        success = "3 received" in result

        return f"{src_name} {'可以✅' if success else '无法❌'} ping 通 {target_host or target_ip}"

    elif action == "delete_flowtable":
        switches = instruction.get("switches", [])
        extra = instruction.get("extra", {})
        match = extra.get("match", {})

        if not switches:
            return "❌ 错误：未指定交换机"

        for sw in switches:
            if sw == "all":
                # 查询所有交换机 ID
                sw_list = get_all_switch_ids()
            else:
                sw_list = [int(sw.replace("s", ""))]

            for dpid in sw_list:
                payload = {
                    "dpid": dpid,
                    "match": match
                }
                try:
                    resp = requests.post("http://localhost:8081/stats/flowentry/delete", json=payload)
                    if resp.status_code != 200:
                        return f"❌ 删除流表失败，交换机 {dpid} 返回码 {resp.status_code}"
                except Exception as e:
                    return f"❌ 删除流表失败: {e}"

        return "✅ 流表删除成功"

    elif action == "shutdown_topology":
        if mm.global_net:
            mm.global_net.stop()
            mm.global_net.delete()
            mm.global_net = None
        return "✅ 拓扑已关闭"

    elif action == "delete_host":
        if not mm.global_net:
            return "❌ 当前没有拓扑"
        target = instruction.get("target")
        node = mm.global_net.get(target)
        if not node:
            return f"❌ 节点 {target} 不存在"
        mm.global_net.delNode(node)
        return f"✅ 已删除节点 {target}"

    else:
        return f"❌ 未识别的指令类型: {action}"
