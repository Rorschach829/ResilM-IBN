import tempfile
import traceback
from mininet.clean import cleanup
from backend.agents.intent_agent import IntentAgent

global_net = None  # 全局保存net实例

def run_mininet_code(code: str) -> str:
    global global_net

    try:
        exec_globals = {}
        # 执行 LLM 生成的 Mininet 代码（需包含 net = Mininet(...)）
        exec(code, exec_globals)

        if "net" not in exec_globals:
            return "错误：代码中未定义 net 对象"

        # 如果已有运行中的拓扑，先停止
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
    global global_net
    if not global_net:
        return {"nodes": [], "edges": []}

    nodes = []
    edges = []

    for host in global_net.hosts:
        nodes.append({"data": {"id": host.name, "type": "host"}})
    for switch in global_net.switches:
        nodes.append({"data": {"id": switch.name, "type": "switch"}})

    for link in global_net.links:
        try:
            intf1 = link.intf1
            intf2 = link.intf2

            if intf1 is None or intf2 is None or intf1.node is None or intf2.node is None:
                print(f"Warning: 无效链路 {link}，跳过")
                continue

            src = intf1.node.name
            dst = intf2.node.name
            edges.append({"data": {"source": src, "target": dst}})
        except Exception as e:
            print(f"处理链路出错: {e}")
            continue

    return {"nodes": nodes, "edges": edges}

def rebuild_topology(intent_json: dict) -> str:
    global global_net

    # cleanup()

    # 若已有拓扑，先销毁
    if global_net:
        try:
            global_net.stop()
            global_net = None
        except Exception as e:
            print(f"销毁旧拓扑失败: {e}")

    code = build_mininet_code_from_json(intent_json)

    exec_globals = {}
    try:
        exec(code, exec_globals)
        global_net = exec_globals.get("net")
        if not global_net:
            raise Exception("生成的代码中未创建 net 实例")
        return "✅ 拓扑创建成功"
    except Exception as e:
        global_net = None
        return f"❌ 拓扑创建失败: {str(e)}"

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
        f"net = Mininet(controller=None)",
        f"c0 = net.addController('c0', controller=RemoteController, ip='{controller['ip']}', port={controller['port']})",
    ]

    # for h in hosts:
    #     lines.append(f"{h} = net.addHost('{h}')")

    # 添加主机并分配ip地址
    for i, h in enumerate(hosts):
        ip = f"10.0.0.{i + 1}"
        lines.append(f"{h} = net.addHost('{h}', ip='{ip}')")

    for s in switches:
        lines.append(f"{s} = net.addSwitch('{s}')")
    for link in links:
        lines.append(f"net.addLink({link['src']}, {link['dst']})")

    lines += [
        "net.start()",
        "# CLI(net)  # 已禁用，为了非阻塞执行",
        ""
    ]

    return "\n".join(lines)
