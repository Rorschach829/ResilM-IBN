# backend/utils/topology_utils.py

import time
import requests
from mininet.util import quietRun

def trigger_controller_learn_hosts(net):
    print("[INTENT] 正在触发主机之间通信，帮助控制器学习主机...")
    try:
        print("[INTENT] 等待主机进程完全稳定...下面马上执行pingALL。信息来自trigger_controller_learn_hosts")
        time.sleep(3)  # 建议延时 2 秒以上
        # 建议使用 pingPairs 更快，避免 broadcast
        net.pingAll(timeout='1')
        print("[PING] ✅ 主机间 ping 完成")
    except Exception as e:
        print(f"[PING] ❌ 主机间 ping 失败: {e}")

def wait_for_stp_convergence(switches_info: dict, timeout: int = 35, interval: int = 5) -> int:
    """
    等待STP控制器收敛：轮询流表状态直到任一交换机出现流表条目。
    :param switches_info: 交换机信息字典 { "s1": {"dpid": 1, "node": <Switch>} }
    :param timeout: 最长等待秒数
    :param interval: 检查间隔秒数
    :return: 实际等待秒数
    """
    waited = 0
    while waited < timeout:
        try:
            for info in switches_info.values():
                dpid = info["dpid"]
                response = requests.get(f"http://localhost:8081/stats/flow/{dpid}", timeout=3)
                if response.status_code == 200:
                    flows = response.json()
                    if len(flows.get(str(dpid), [])) > 0:
                        time.sleep(5)  # 稳定等待
                        return waited + 5
        except Exception as e:
            pass
        time.sleep(interval)
        waited += interval
    return timeout

# 文件: backend/utils/topology_utils.py

import networkx as nx

def build_networkx_graph_from_mininet(net):
    """
    根据 Mininet 拓扑结构构建 NetworkX 图，用于路径计算。
    节点名为主机名和交换机名（如 h1, s1 等），边为链路。
    """
    graph = nx.Graph()

    for link in net.links:
        node1 = link.intf1.node
        node2 = link.intf2.node
        name1 = node1.name
        name2 = node2.name
        graph.add_edge(name1, name2)

    return graph


def safe_ping(h1, h2):
    """
    安全触发 ping，防止 Mininet 主机未准备好时抛异常
    """
    try:
        h1.cmd(f"ping -c1 -W1 {h2.IP()} > /dev/null 2>&1")
        print(f"[PING] ✅ {h1.name} -> {h2.name} 成功")
    except Exception as e:
        print(f"[WARN] ❌ {h1.name} ping {h2.name} 失败: {e}")
