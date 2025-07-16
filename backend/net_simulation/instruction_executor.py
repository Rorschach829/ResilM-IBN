import json
import backend.net_simulation.mininet_manager as mm  # ✅ 用模块别名导入
from backend.net_simulation.ryu_controller import send_flow_mod
import requests
from backend.utils.ryu_utils import get_all_switch_ids
from backend.utils.utils import convert_switch_name_to_dpid
from ryu_app.auto_generate_path_intents import build_and_send_all_path_intents
from backend.net_simulation import net_bridge
from backend.utils.logger import start_new_intent_log, log_intent
from backend.net_simulation.mininet_manager import stop_topology
# from backend.utils.topology_utils import ping_pairs_multi_thread_safe, ping_pairs_single_thread
import mininet.log
from contextlib import redirect_stdout
import sys
import time
import re
import os
import io
import traceback

# 在执行link_up的恢复网络操作时，跳过以下actions
SKIP_ACTIONS_ON_RECOVERY = {
    "ping_test",
    "get_flowtable",
    "verify_bandwidth"
}

def convert_switch_name_to_dpid(name: str) -> int:
    """
    将交换机名（如 's1'）转换为对应的 dpid（数字）
    """
    if name.startswith("s"):
        return int(name[1:])
    raise ValueError(f"无法识别的交换机名: {name}")

# 根据LLM输出的不同action进行不同操作
def execute_instruction(instruction: dict) -> str:
    action = instruction.get("action")

    if action == "create_topology":
        
        # 当创建新拓扑的时候，新建json记录文件
        start_new_intent_log()

        # ✅ 清空 controller 注册状态，防止重复注册主机
        from backend.controller import controller_instance
        controller = controller_instance.get_controller_instance()
        result = mm.rebuild_topology(instruction)

        net_bridge.global_net = mm.global_net
        print("[DEBUG] mm module ID:", id(mm))
        print(f"[DEBUG] 拓扑创建结果: {result}")

        net = mm.global_net

        if net:
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
    
    # 断开链路
    elif action == "link_down":
        print("[DEBUG] Flask 正准备调用 Ryu 的 /intent/link_down 接口")
        # ✅ 在 link_down 前注入 global_net 给 Ryu 控制器
        from backend.controller import controller_instance
        ryu_controller = controller_instance.get_controller_instance()
        if ryu_controller:
            ryu_controller.mininet_net = net_bridge.global_net
            print("[DEBUG] 已注入 global_net 到 Ryu 控制器:", id(net_bridge.global_net))
        try:
            resp = requests.post(
                "http://localhost:8081/intent/link_down",
                json={"link": instruction.get("link", [])},
                timeout=2
            )
            print("[DEBUG] Ryu link_down 接口返回状态:", resp.status_code)
            if resp.status_code == 200:
                return resp.text
            else:
                return f"❌ 控制器返回错误: {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"❌ 无法连接控制器 REST 接口: {e}"

# 恢复链路，原理是恢复当前的网络操作并且跳过link_down
    elif action == "link_up":
        from backend.utils.logger import CURRENT_LOG_FILE
        if not CURRENT_LOG_FILE or not os.path.exists(CURRENT_LOG_FILE):
            return "❌ 当前 session 没有找到日志文件，无法执行 link_up"

        try:
            target_link = instruction.get("link", [])
            link_variants = [target_link, target_link[::-1]]  # 支持 ["s1", "s2"] 或 ["s2", "s1"]

            # Step 1: 读取所有意图，跳过指定 link_down
            with open(CURRENT_LOG_FILE, "r", encoding="utf-8") as f:
                blocks = f.read().split("\n\n")
                instructions = []
                for block in blocks:
                    if not block.strip():
                        continue
                    entry = json.loads(block)
                    instr = entry.get("instruction", {})
                    if not instr:
                        continue

                    # 跳过那个断链link_down的操作
                    if instr.get("action") == "link_down" and instr.get("link") in link_variants:
                        print(f"[SKIP] 跳过断链: {instr['link']}")
                        continue

                    # 跳过无副作用动作
                    if instr.get("action") in SKIP_ACTIONS_ON_RECOVERY:
                        print(f"[SKIP] 跳过无副作用动作: {instr['action']}")
                        continue
                    
                    instructions.append(instr)

            # Step 2: 执行重建
            stop_topology()
            from backend.controller import controller_instance
            ctl = controller_instance.get_controller_instance()
            if ctl:
                ctl.reset_state()
            else:
                print("[WARN] 获取 PathIntentController 实例失败，无法清空控制器状态")

            results = []
            for idx, instr in enumerate(instructions):
                action = instr.get("action")
                result = execute_instruction(instr)
                results.append(f"[REPLAY 回放动作 {idx+1}] [{action}] => {result}")

            return "✅ link_up 完成，已恢复拓扑并保留其他断链操作\n" + "\n".join(results)

        except Exception as e:
            return f"❌ link_up 执行失败: {e}"

# 对主机限速
    # elif action == "limit_bandwidth":
    #     src = instruction.get("src_host")
    #     dst = instruction.get("dst_host")
    #     rate = instruction.get("rate_mbps")

    #     if not mm.global_net:
    #         return "❌ 当前没有拓扑"

    #     src_host = mm.global_net.get(src)
    #     if not src_host:
    #         return f"❌ 源主机 {src} 不存在"

    #     # 假设限速从 src 发出的所有流量（对 dst 限速，可拓展为双向限速）
    #     try:
    #         dev = src_host.name + "-eth0"
    #         rate_str = f"{rate}mbit"
    #         burst = "20kb"
    #         latency = "70ms"
    #         cmd = f"tc qdisc add dev {dev} root tbf rate {rate_str} burst {burst} latency {latency}"
    #         result = src_host.cmd(cmd)

    #         return f"✅ 限速设置成功: {src} → {dst}, 速率限制为 {rate}Mbps\n执行结果:\n{result}"
    #     except Exception as e:
    #         return f"❌ 限速失败: {e}"

    # 对主机测速
    elif action == "limit_bandwidth":
        src = instruction.get("src_host")
        dst = instruction.get("dst_host")
        rate = instruction.get("rate_mbps")

        if not mm.global_net:
            return "❌ 当前没有拓扑"

        src_host = mm.global_net.get(src)
        if not src_host:
            return f"❌ 找不到主机 {src}"

        try:
            dev = f"{src}-eth0"
            rate_str = f"{rate}mbit"
            cmds = [f"tc qdisc del dev {dev} root"]

            if dst:
                dst_host = mm.global_net.get(dst)
                if not dst_host:
                    return f"❌ 找不到目标主机 {dst}"
                dst_ip = dst_host.IP()

                # 单向限速（仅 h1 → h2）
                cmds += [
                    f"tc qdisc add dev {dev} root handle 1: htb default 12",
                    f"tc class add dev {dev} parent 1: classid 1:1 htb rate {rate_str}",
                    f"tc filter add dev {dev} protocol ip parent 1: prio 1 u32 match ip dst {dst_ip} flowid 1:1"
                ]
                result = f"✅ 成功设置单向限速：{src} → {dst} 为 {rate}Mbps"
            else:
                # 全局限速（h1 到所有主机都限）
                cmds += [
                    f"tc qdisc add dev {dev} root tbf rate {rate_str} burst 20kb latency 70ms"
                ]
                result = f"✅ 成功设置全局限速：{src} 发往所有主机为 {rate}Mbps"

            for c in cmds:
                src_host.cmd(c)

            return result

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
            # return f"📊 带宽测试结果 (h1 → h2):\n{result}"
            return f"📊 带宽测试结果 ({src} → {dst}):\n{result}"

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

    # 测试所有主机连通性
    # 后续可加入结构化输出（JSON），方便前端展示和 agent 分析
    elif action == "ping_all":
        if not mm.global_net:
            return "❌ 当前没有拓扑"
        net = mm.global_net
        try:
            print("=== 多线程双向ping_all测试===")
            from backend.utils.topology_utils import robust_ping_pairs_multi_thread

            res = robust_ping_pairs_multi_thread(mm.global_net)

            failed_pairs = res["failed_pairs"]
            total = res["total"]
            success = res["success"]

            if not failed_pairs:
                return f"✅ 所有主机均可互相通信，共测试 {total} 对"
            else:
                failed_lines = [f"- {src} → {dst}" for src, dst in failed_pairs]
                summary = f"✅ 其余 {success} 对主机通信正常"
                return "❌ 以下主机对无法通信：\n" + "\n".join(failed_lines) + "\n" + summary
      
        except Exception as e:
            return f"❌ 执行ping_all失败: {e}"



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
