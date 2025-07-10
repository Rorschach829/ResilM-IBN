import tempfile
import traceback
from backend.agents.intent_agent import IntentAgent
from mininet.clean import cleanup



global_net = None  # 全局保存net实例

def run_mininet_code(code: str) -> str:
    global global_net

    try:
        exec_globals = {}
        # 执行LLM生成的代码（代码中需包含 net = Mininet(...) 和 net.start()，但不要调用 net.stop()）
        exec(code, exec_globals)

        # 检查是否成功创建了 net 对象
        if "net" not in exec_globals:
            return "错误：代码中未定义 net 对象"
        
        # 如果之前有运行中的拓扑，先停止清理
        if global_net:
            try:
                global_net.stop()
            except Exception:
                pass

        global_net = exec_globals["net"]
        return "拓扑启动成功，网络已激活"

    except Exception as e:
        tb = traceback.format_exc()
        return f"执行错误: {str(e)}\n{tb}"

def get_current_topology():
    """
    从 global_net 中获取拓扑信息，转换成前端需要的 JSON 结构。
    返回格式示例：
    {
      "nodes": [{"data": {"id": "h1", "type": "host"}}, ...],
      "edges": [{"data": {"source": "h1", "target": "s1"}}, ...]
    }
    """
    global global_net
    if not global_net:
        return {"nodes": [], "edges": []}

    nodes = []
    edges = []

    # 添加所有主机和交换机节点
    for host in global_net.hosts:
        nodes.append({"data": {"id": host.name, "type": "host"}})
    for switch in global_net.switches:
        nodes.append({"data": {"id": switch.name, "type": "switch"}})

    # 添加所有链路边
    for link in global_net.links:
        try:
            intf1 = link.intf1
            intf2 = link.intf2

            # 安全判断接口和接口节点是否存在
            if intf1 is None or intf2 is None:
                print(f"Warning: Link {link} has None interface, skipped")
                continue
            if intf1.node is None or intf2.node is None:
                print(f"Warning: Link {link} has interface with None node, skipped")
                continue

            src = intf1.node.name
            dst = intf2.node.name

            edges.append({"data": {"source": src, "target": dst}})
        except Exception as e:
            print(f"Error processing link {link}: {e}")
            continue

    return {"nodes": nodes, "edges": edges}

def rebuild_topology(intent_text: str) -> str:
    agent = IntentAgent()
    intent_json = agent.intent_to_instruction(intent_text)

    global global_net
    cleanup()
    # 1. 如果已有拓扑，先销毁它
    if global_net:
        try:
            global_net.stop()
            global_net = None
        except Exception as e:
            print(f"销毁旧拓扑失败: {e}")

    # 2. 调用大语言模型生成新拓扑代码
    code = build_mininet_code_from_json(intent_json)

    # 3. 执行生成的代码，创建新的global_net实例
    exec_globals = {}
    try:
        exec(code, exec_globals)
        # 假设代码里有个变量net是Mininet实例
        new_net = exec_globals.get("net")
        if not new_net:
            raise Exception("生成代码中没有定义 net 实例")
        global_net = new_net
    except Exception as e:
        raise Exception(f"重建拓扑失败: {e}")

    return code

def stop_topology() -> str:
    global global_net
    if not global_net:
        return "当前没有运行中的拓扑"

    try:
        global_net.stop()
        global_net = None
        return "拓扑已成功停止"
    except Exception as e:
        return f"停止拓扑失败: {str(e)}"

# 从json中生成控制mininet的代码
def build_mininet_code_from_json(data: dict) -> str:
    hosts = data.get("hosts", [])
    switches = data.get("switches", [])
    links = data.get("links", [])
    controller = data.get("controller", {"type": "RemoteController", "ip": "127.0.0.1", "port": 6633})

    lines = [
        "from mininet.net import Mininet",
        "from mininet.cli import CLI",
        "from mininet.log import setLogLevel",
        "from mininet.node import RemoteController",
        "",
        "setLogLevel('info')",
        "",
        f"net = Mininet(controller=RemoteController)",
        f"c0 = net.addController('c0', controller=RemoteController, ip='{controller['ip']}', port={controller['port']})",
    ]

    for h in hosts:
        lines.append(f"{h} = net.addHost('{h}')")

    for s in switches:
        lines.append(f"{s} = net.addSwitch('{s}')")

    for link in links:
        lines.append(f"net.addLink({link['src']}, {link['dst']})")

    lines += [
        "net.start()",
        "# 运行 CLI 已禁用，为了非阻塞执行",
        "# CLI(net)",
        "# 你可以用 net.pingAll() 替代命令行测试",
        ""
    ]

    return "\n".join(lines)
