import json
import backend.net_simulation.mininet_manager as mm  # ✅ 用模块别名导入
from backend.net_simulation.ryu_controller import send_flow_mod
import requests
from backend.utils.ryu_utils import get_all_switch_ids
from backend.utils.utils import convert_switch_name_to_dpid
from ryu_app.auto_generate_path_intents import build_and_send_all_path_intents
import time
import re
def convert_switch_name_to_dpid(name: str) -> int:
    """
    将交换机名（如 's1'）转换为对应的 dpid（数字）
    """
    if name.startswith("s"):
        return int(name[1:])
    raise ValueError(f"无法识别的交换机名: {name}")

def execute_instruction(instruction: dict) -> str:
    action = instruction.get("action")

    if action == "create_topology":
        result = mm.rebuild_topology(instruction)
        print(f"[DEBUG] 拓扑创建结果: {result}")

        net = mm.global_net

        if net:
            from backend.utils.topology_utils import trigger_controller_learn_hosts
            try:
                trigger_controller_learn_hosts(net)
            except Exception as e:
                print(f"[WARN] trigger_controller_learn_hosts 执行失败: {e}")

            expected_hosts = len(net.hosts)
            if wait_for_all_hosts(expected=expected_hosts, timeout=15):
                build_and_send_all_path_intents(net)
                print("[INTENT] 路径流表下发完成 ✅")
            else:
                print(f"[INTENT] ❌ 等待超时，期望注册 {expected_hosts} 台主机，实际不足")

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

        src_name = instruction.get("extra", {}).get("source") or instruction.get("source")
        target_ip = instruction.get("extra", {}).get("target") or instruction.get("target")
        target_host = instruction.get("extra", {}).get("target_host") or instruction.get("target")

        if not src_name or not target_ip:
            return "❌ 指令缺少 source 或 target"

        src_host = mm.global_net.get(src_name)
        if not src_host:
            return f"❌ 主机 {src_name} 不存在"

        # 发送3个包，有一个包收到了就说明Ping通了
        print(f"[PING] 第一次尝试: {src_name} -> {target_ip}")
        result1 = src_host.cmd(f"ping -c 3 -W 1 {target_ip}")
        match1 = re.search(r"(\d+) packets transmitted, (\d+) received", result1)
        success1 = match1 and int(match1.group(2)) >= 1

        if success1:
            return f"{src_name} 可以✅ ping 通 {target_host or target_ip}\n{result1}"

        # 等待5秒控制器可能下发流表
        print(f"[PING] 第一次失败，等待 5 秒后重试...")
        time.sleep(5)

        print(f"[PING] 第二次尝试: {src_name} -> {target_ip}")
        result2 = src_host.cmd(f"ping -c 3 -W 1 {target_ip}")
        match2 = re.search(r"(\d+) packets transmitted, (\d+) received", result2)
        success2 = match2 and int(match2.group(2)) >= 1

        return f"{src_name} {'可以✅' if success2 else '无法❌'} ping 通 {target_host or target_ip}\n{result2}"


    elif action == "delete_flowtable":
        switches = instruction.get("switches", [])

        # 支持 match 字段既可能在 extra 中，也可能在顶层
        extra = instruction.get("extra", {})
        match = extra.get("match") or instruction.get("match", {})

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

    elif action == "get_flowtable":
        switches = instruction.get("switches", [])
        results = []

        for sw in switches:
            dpid = convert_switch_name_to_dpid(sw)
            url = f"http://localhost:8081/stats/flow/{dpid}"
            print("[DEBUG] 请求 URL:", url)
            try:
                resp = requests.get(url)
                if resp.status_code == 200:
                    flows = resp.json().get(str(dpid), [])
                    formatted = json.dumps(flows, indent=2, ensure_ascii=False)
                    results.append(f"✅ 交换机 {sw} 当前流表:\n{formatted}")
                else:
                    results.append(f"❌ 无法获取交换机 {sw} 的流表")
            except Exception as e:
                results.append(f"❌ 请求失败: {e}")

        return "\n\n".join(results)


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

# 对主机限速
    elif action == "limit_bandwidth":
        src = instruction.get("src_host")
        dst = instruction.get("dst_host")
        rate = instruction.get("rate_mbps")

        if not mm.global_net:
            return "❌ 当前没有拓扑"

        src_host = mm.global_net.get(src)
        if not src_host:
            return f"❌ 源主机 {src} 不存在"

        # 假设限速从 src 发出的所有流量（对 dst 限速，可拓展为双向限速）
        try:
            dev = src_host.name + "-eth0"
            rate_str = f"{rate}mbit"
            burst = "20kb"
            latency = "70ms"
            cmd = f"tc qdisc add dev {dev} root tbf rate {rate_str} burst {burst} latency {latency}"
            result = src_host.cmd(cmd)

            return f"✅ 限速设置成功: {src} → {dst}, 速率限制为 {rate}Mbps\n执行结果:\n{result}"
        except Exception as e:
            return f"❌ 限速失败: {e}"
# 对主机测速
    elif action == "verify_bandwidth":
        src = instruction.get("src_host")
        dst = instruction.get("dst_host")

        if not mm.global_net:
            return "❌ 当前没有拓扑"

        src_host = mm.global_net.get(src)
        dst_host = mm.global_net.get(dst)

        if not src_host or not dst_host:
            return f"❌ 找不到主机 {src} 或 {dst}"

        try:
            # 启动目标主机 iperf 服务器, TCP模式
            dst_host.cmd("iperf -s  -D")
            time.sleep(1)

            # 源主机发起 iperf 的TCP测试
            result = src_host.cmd(f"iperf -c {dst_host.IP()} -t 5")
            return f"📊 带宽测试结果 (h1 → h2):\n{result}"
        except Exception as e:
            return f"❌ 带宽测试失败: {e}"

    elif action == "clear_bandwidth_limit":
        host = instruction.get("host")

        if not mm.global_net:
            return "❌ 当前没有拓扑"

        target = mm.global_net.get(host)
        if not target:
            return f"❌ 主机 {host} 不存在"

        try:
            dev = f"{host}-eth0"
            cmd = f"tc qdisc del dev {dev} root"
            result = target.cmd(cmd)

            return f"✅ 已取消主机 {host} 的限速设置\n执行结果:\n{result}"
        except Exception as e:
            return f"❌ 取消限速失败: {e}"


    else:
        return f"❌ 未识别的指令类型: {action}"

def wait_for_all_hosts(expected=9, timeout=10):
    import requests
    import time

    for _ in range(timeout):
        try:
            resp = requests.get("http://localhost:8081/intent/valid_hosts")
            if resp.status_code == 200:
                hosts = resp.json()
                print(f"[等待主机] 当前已注册 {len(hosts)} 个主机: {hosts}")
                if len(hosts) >= expected:
                    return True
        except Exception as e:
            print(f"[等待主机] 请求失败: {e}")
        time.sleep(1)
    return False
