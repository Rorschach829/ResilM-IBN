import requests

# networkx用来解析mininet拓扑结构，计算主机之间的最短路径
import networkx as nx

def build_and_send_all_path_intents(net, controller_url="http://localhost:8081"):
    """
    根据 Mininet 拓扑自动生成所有主机间的路径意图流表，并下发至控制器。
    要求控制器支持 POST /intent/flow 接口。
    """
    print("🚀 正在自动生成并下发所有主机间流表意图...")

    hosts = net.hosts
    switches = net.switches
    links = net.links

    # 提取主机名称与 IP
    host_info = {h.name: h.IP() for h in hosts}

    # 构建 NetworkX 拓扑图
    topo = nx.Graph()
    for link in links:
        node1, node2 = link.intf1.node.name, link.intf2.node.name
        topo.add_edge(node1, node2)

    count = 0
    for src_name, src_ip in host_info.items():
        for dst_name, dst_ip in host_info.items():
            if src_name == dst_name:
                continue

            # 找出路径，例如 h1 -> s1 -> s2 -> s3 -> h9
            try:
                path = nx.shortest_path(topo, src_name, dst_name)
            except nx.NetworkXNoPath:
                print(f"❌ 无法找到 {src_name} 到 {dst_name} 的路径")
                continue

            # 提取交换机路径，如 [s1, s2, s3]
            switch_path = [node for node in path if node.startswith("s")]

            if not switch_path:
                continue  # 两主机直连跳过

            # 构造意图
            intent = {
                "source": src_name,
                "target": dst_name,
                "path": switch_path,
                "extra": {
                    "match": {
                        "dl_type": 2048,
                        "nw_src": src_ip,
                        "nw_dst": dst_ip,
                        "nw_proto": 1
                    },
                    "actions": "ALLOW",
                    "priority": 100
                }
            }

            # 下发意图
            try:
                response = requests.post(f"{controller_url}/intent/flow", json=intent)
                if response.status_code == 200:
                    print(f"✅ 成功安装流表: {src_name} -> {dst_name} via {switch_path}")
                    count += 1
                else:
                    print(f"❌ 安装失败: {src_name} -> {dst_name}, 状态码: {response.status_code}")
            except Exception as e:
                print(f"❌ 请求失败: {e}")

    print(f"🎉 共下发 {count} 条路径意图流表。主机间通信已打通！")
