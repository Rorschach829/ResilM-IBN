from backend.net_simulation.mininet_manager import rebuild_topology, global_net
import json

def execute_instruction(instruction: dict) -> str:
    action = instruction.get("action")

    if action == "create_topology":
        return rebuild_topology(instruction)  # 自动调用 net.stop(), 清理旧拓扑再创建

    elif action == "ping_test":
        if not global_net:
            return "❌ 当前没有拓扑"
        src = instruction.get("src")
        dst = instruction.get("dst")
        src_host = global_net.get(src)
        if not src_host:
            return f"❌ 源主机 {src} 不存在"
        return src_host.cmd(f"ping -c 1 {dst}")

    elif action == "delete_host":
        if not global_net:
            return "❌ 当前没有拓扑"
        target = instruction.get("target")
        node = global_net.get(target)
        if not node:
            return f"❌ 节点 {target} 不存在"
        global_net.delNode(node)
        return f"✅ 已删除节点 {target}"

    elif action == "shutdown_topology":
        if global_net:
            global_net.stop()
            global_net.delete()
        return "✅ 拓扑已关闭"

    else:
        return f"❌ 未识别的指令类型: {action}"
