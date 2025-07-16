# backend/utils/topology_utils.py
import concurrent.futures
import time
import requests
from mininet.util import quietRun
import networkx as nx
from concurrent.futures import ThreadPoolExecutor
import re
import threading
import itertools

def trigger_controller_learn_hosts(net):
    print("[INTENT] 正在触发主机之间通信，帮助控制器学习主机...")
    try:
        print("[INTENT] 等待主机进程完全稳定...马上ping_pairs。信息来自trigger_controller_learn_hosts")
        # time.sleep(2)  # 建议延时 2 秒以上
        print(fast_host_activation(net, timeout=1))
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

# 让每台主机主动发送一次数据包，
# 仅用于触发 PacketIn，从而使控制器得以感知该主机的 MAC、IP、所连交换机及端口信息
def ping_once_per_host(net, timeout=1):
    hosts = net.hosts
    output_lines = ["*** Trigger PacketIn by one ping per host"]

    start = time.time()  # ⏱️ 开始计时

    for i, src in enumerate(hosts):
        dst = hosts[(i + 1) % len(hosts)]  # 环形 ping
        result = src.cmd(f"ping -c1 -W{timeout} {dst.IP()}")

        ok = "1 packets transmitted, 1 received" in result or "0% packet loss" in result
        output_lines.append(f"{src.name} -> {dst.name}: {'OK' if ok else 'X'}")

    end = time.time()  # ⏱️ 结束计时
    elapsed = round(end - start, 4)
    output_lines.append(f"⏱️ 耗时: {elapsed} 秒")

    return "\n".join(output_lines)

# ping_once_per_host的升级版，一次性向3台主机发数据包，提高packetin的概率
def ping_once_multi_target(net, timeout=1):
    hosts = net.hosts
    output_lines = ["*** Ping per host to multiple targets"]
    start = time.time()  # ⏱️ 开始计时
    for i, src in enumerate(hosts):
        # ping 3 个目标，错开热点
        for offset in [7, 13, 19]:
            dst = hosts[(i + offset) % len(hosts)]
            result = src.cmd(f"ping -c1 -W{timeout} {dst.IP()}")
            ok = "1 received" in result or "0% packet loss" in result
            output_lines.append(f"{src.name} -> {dst.name}: {'OK' if ok else 'X'}")
    
    end = time.time()  # ⏱️ 结束计时
    elapsed = round(end - start, 4)
    output_lines.append(f"⏱️ 总耗时: {elapsed} 秒")
    return "\n".join(output_lines)


# 多线程双向ping_pairs,建议多使用这个函数
# 只判断收到的包是否大于等于1，如果大于等于1说明ping通了
def ping_pairs_multi_thread_safe(net, max_workers=20, batch_size=50):
    hosts = net.hosts
    total_pairs = list(itertools.permutations(hosts, 2))
    total = len(total_pairs)
    results = {}

    # 每个主机一个锁，避免并发访问
    host_locks = {host.name: threading.Lock() for host in hosts}
    global_lock = threading.Lock()

    def is_ping_success(output):
        if "0 received" in output or "100% packet loss" in output:
            return False
        if "Destination Host Unreachable" in output or "Network is unreachable" in output:
            return False
        return True

    def ping_and_store(src, dst, idx):
        # 使用各自主机的锁
        with host_locks[src.name], host_locks[dst.name]:
            result = src.cmd(f"ping -c 1 -W 1 {dst.IP()}")
            ok = is_ping_success(result)
            with global_lock:
                results[(src.name, dst.name)] = "OK" if ok else "X"
                if not ok:
                    print(f"[失败] {src.name} → {dst.name} 无法连通")
                if idx % 50 == 0 or idx == total:
                    print(f"[进度] 已完成 {idx}/{total} 条 ping 测试")

    print(f"[开始] 共 {total} 对主机进行 ping 测试，线程池大小为 {max_workers}，每批次 {batch_size} 条")
    start_time = time.time()

    for i in range(0, total, batch_size):
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            batch = total_pairs[i:i+batch_size]
            futures = []
            for idx, (src, dst) in enumerate(batch, start=i+1):
                futures.append(executor.submit(ping_and_store, src, dst, idx))
            for future in futures:
                future.result()
        time.sleep(0.5)

    elapsed = time.time() - start_time
    print(f"[完成] 所有主机对 ping 测试已完成，总耗时：{elapsed:.2f} 秒")
    
    return {
        "total": total,
        "success": sum(1 for v in results.values() if v == "OK"),
        "failed_pairs": [(src, dst) for (src, dst), v in results.items() if v != "OK"]
    }


# def ping_pairs_multi_thread_safe(net, timeout=1):
#     hosts = net.hosts
#     results = []

#     def ping_from(src):
#         line_results = []
#         for dst in hosts:
#             if src == dst:
#                 continue
            
#             result = src.cmd(f"ping -c3 -W1 {dst.IP()}")
#             match = re.search(r"(\d+) packets transmitted, (\d+) received", result)
#             ok = match and int(match.group(2)) >= 1

#             line_results.append(f"{src.name} -> {dst.name}: {'OK' if ok else 'X'}")
#         return line_results

    
#     start = time.time()

#     with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
#         futures = [executor.submit(ping_from, src) for src in hosts]
#         for f in concurrent.futures.as_completed(futures):
#             results.extend(f.result())

#     end = time.time()
#     print(f"⚡ 多线程（按主机并发）ping_pairs 耗时: {end - start:.4f} 秒")
#     return results


# 单线程双向ping_pairs
def ping_pairs_single_thread(net, timeout=1):
    hosts = net.hosts
    results = []
    start = time.time()

    for i in range(len(hosts)):
        for j in range(i + 1, len(hosts)):
            src = hosts[i]
            dst = hosts[j]

            result1 = src.cmd(f"ping -c1 -W{timeout} {dst.IP()}")
            result2 = dst.cmd(f"ping -c1 -W{timeout} {src.IP()}")

            ok1 = "1 packets transmitted, 1 received" in result1 or "0% packet loss" in result1
            ok2 = "1 packets transmitted, 1 received" in result2 or "0% packet loss" in result2

            results.append(f"{src.name} -> {dst.name}: {'OK' if ok1 else 'X'}")
            results.append(f"{dst.name} -> {src.name}: {'OK' if ok2 else 'X'}")

    end = time.time()
    print(f"🔹 单线程双向 ping_pairs 耗时: {end - start:.4f} 秒")
    return results

# 用于创建拓扑时快速激活主机
def fast_host_activation(net, timeout=1):
    """
    真正并发触发所有主机对的 ping（只发一次包），用于控制器学习。
    """
    hosts = net.hosts
    output_lines = ["*** 快速主机唤醒（全并发触发 PacketIn）"]

    start = time.time()

    def ping_once_pair(i):
        src = hosts[i]
        dst = hosts[(i + 1) % len(hosts)]
        result = src.cmd(f"ping -c1 -W{timeout} {dst.IP()}")
        ok = "1 packets transmitted, 1 received" in result or "0% packet loss" in result
        return f"{src.name} -> {dst.name}: {'OK' if ok else 'X'}"

    with ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(ping_once_pair, i) for i in range(len(hosts))]
        for f in futures:
            output_lines.append(f.result())

    end = time.time()
    elapsed = round(end - start, 4)
    output_lines.append(f"⏱️ 并发唤醒完成，耗时: {elapsed} 秒")
    return "\n".join(output_lines)
