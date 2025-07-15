import requests
import time
import networkx as nx
from backend.utils.topology_utils import build_networkx_graph_from_mininet
def build_and_send_all_path_intents(net):
    """
    对网络中每一对主机生成最短路径流表，并下发到 Ryu 控制器。
    """
    hosts = net.hosts
    host_names = [h.name for h in hosts]

    # 获取拓扑图
    topo_graph = build_networkx_graph_from_mininet(net)
    if not nx.is_connected(topo_graph.to_undirected()):
        print("[INTENT] ❌ 网络图不连通，路径下发中止")
        return

    # 构建最小生成树以避免环路
    tree = nx.minimum_spanning_tree(topo_graph.to_undirected())
    print("[INTENT] 拓扑图转换为最小生成树成功，开始遍历主机对...")

    success_count = 0
    fail_count = 0

    for src_name in host_names:
        for dst_name in host_names:
            if src_name == dst_name:
                continue
            path = nx.shortest_path(tree, source=src_name, target=dst_name)
            print(f"🚀 Path intent: {src_name} → {dst_name} 路径: {path}")

            src_mac = net.get(src_name).MAC()
            dst_mac = net.get(dst_name).MAC()

            try:
                resp = requests.post("http://127.0.0.1:8081/intent/flow", json={
                    "src_host": src_mac,
                    "dst_host": dst_mac
                })
                if resp.status_code == 200:
                    success_count += 1
                else:
                    fail_count += 1
                    print(f"❌ 路径下发失败: {src_name} → {dst_name}, 状态码: {resp.status_code}")
            except Exception as e:
                fail_count += 1
                print(f"❌ 请求异常: {src_name} → {dst_name}, 错误: {e}")

    print(f"[INTENT] 流表下发完成: 成功 {success_count} 对，失败 {fail_count} 对")
