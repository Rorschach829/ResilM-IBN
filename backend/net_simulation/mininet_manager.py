import tempfile
import traceback
from mininet.clean import cleanup
from backend.agents.intent_agent import IntentAgent
from backend.utils.utils import is_cyclic_topology
from backend.utils.arp_utils import configure_static_arp
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
        return {"nodes": [], "links": []}

    nodes = []
    links = []

    for host in global_net.hosts:
        nodes.append({"id": host.name, "type": "host"})
    for switch in global_net.switches:
        nodes.append({"id": switch.name, "type": "switch"})

    for link in global_net.links:
        try:
            intf1 = link.intf1
            intf2 = link.intf2

            if intf1 is None or intf2 is None or intf1.node is None or intf2.node is None:
                print(f"Warning: 无效链路 {link}，跳过")
                continue

            src = intf1.node.name
            dst = intf2.node.name
            links.append({"source": src, "target": dst})
        except Exception as e:
            print(f"处理链路出错: {e}")
            continue

    return {"nodes": nodes, "links": links}

def rebuild_topology(intent_json: dict) -> str:
    global global_net

    # 先判断是否为环路拓扑
    enable_stp = is_cyclic_topology(intent_json.get("links", []))
    print(f"[INFO] 当前拓扑是否为环路结构: {enable_stp}")

    if global_net:
        try:
            global_net.stop()
            global_net = None
        except Exception as e:
            print(f"销毁旧拓扑失败: {e}")

    # ✅ 传入 STP 控制参数
    code = build_mininet_code_from_json(intent_json, enable_stp=enable_stp)

    exec_globals = {}
    try:
        exec(code, exec_globals)

        # 手动调用静态 ARP 配置（在 exec 后）
        hosts_info = exec_globals.get("hosts_info")
        if hosts_info:
            configure_static_arp(hosts_info)

        global_net = exec_globals.get("net")
        if not global_net:
            raise Exception("生成的代码中未创建 net 实例")
        return "✅ 拓扑创建成功"
    except Exception as e:
        global_net = None
        return f"❌ 拓扑创建失败: {str(e)}"



# 原版
# def rebuild_topology(intent_json: dict) -> str:
#     global global_net

#     # cleanup()

#     # 若已有拓扑，先销毁
#     if global_net:
#         try:
#             global_net.stop()
#             global_net = None
#         except Exception as e:
#             print(f"销毁旧拓扑失败: {e}")

#     code = build_mininet_code_from_json(intent_json)

#     exec_globals = {}
#     try:
#         exec(code, exec_globals)
#         global_net = exec_globals.get("net")
#         if not global_net:
#             raise Exception("生成的代码中未创建 net 实例")
#         return "✅ 拓扑创建成功"
#     except Exception as e:
#         global_net = None
#         return f"❌ 拓扑创建失败: {str(e)}"

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

def build_mininet_code_from_json(data: dict, enable_stp: bool = True) -> str:
    hosts = data.get("hosts", [])
    switches = data.get("switches", [])
    links = data.get("links", [])
    controller = data.get("controller", {"type": "RemoteController", "ip": "127.0.0.1", "port": 6633})
    
    # 动态生成主机IP映射
    host_ip_map = {}
    for i, host in enumerate(hosts):
        host_ip_map[host] = f"10.0.0.{i + 1}"
    
    # 动态生成交换机DPID映射
    switch_dpid_map = {}
    for i, switch in enumerate(switches):
        switch_dpid_map[switch] = i + 1

    lines = [
        "from mininet.net import Mininet",
        "from mininet.cli import CLI", 
        "from mininet.log import setLogLevel",
        "from mininet.node import RemoteController",
        "import time",
        "import requests",
        "import json",
        "",
        "setLogLevel('info')",
        "",
        f"net = Mininet(controller=None)",
        f"c0 = net.addController('c0', controller=RemoteController, ip='{controller['ip']}', port={controller['port']})",
        "",
        "# 动态添加主机",
        "hosts_info = {}"
    ]

    # 动态添加主机
    for host in hosts:
        ip = host_ip_map[host]
        lines.append(f"{host} = net.addHost('{host}', ip='{ip}')")
        lines.append(f"hosts_info['{host}'] = {{'ip': '{ip}', 'node': {host}}}")

    lines.append("")
    lines.append("# 动态添加交换机")
    lines.append("switches_info = {}")
    
    # 动态添加交换机
    for switch in switches:
        dpid = switch_dpid_map[switch]
        lines.append(f"{switch} = net.addSwitch('{switch}')")
        lines.append(f"switches_info['{switch}'] = {{'dpid': {dpid}, 'node': {switch}}}")

    lines.append("")
    lines.append("# 动态添加链路")
    for link in links:
        lines.append(f"net.addLink({link['src']}, {link['dst']})")

    lines += [
        "",
        "net.start()",
        "",
        "# 禁用所有主机 IPv6",
        "for h in net.hosts:",
        "    h.cmd('sysctl -w net.ipv6.conf.all.disable_ipv6=1')",
        "",
        "# 显示动态网络信息",
        "print('\\n=== 动态网络拓扑信息 ===')",
        "print(f'主机数量: {len(hosts_info)}')",
        "for host_name, info in hosts_info.items():",
        "    print(f'{host_name}: {info[\"ip\"]} (MAC: {info[\"node\"].MAC()})')",
        "",
        "print(f'\\n交换机数量: {len(switches_info)}')",
        "for switch_name, info in switches_info.items():",
        "    print(f'{switch_name}: DPID {info[\"dpid\"]} ({info[\"node\"].dpid})')",
        "",
        "print('\\n=== 链路信息 ===')",
        "for link in net.links:",
        "    print(f'{link.intf1.node.name}({link.intf1.name}) <-> {link.intf2.node.name}({link.intf2.name})')",
        "",

        f"if {str(enable_stp)}:",
        "    print('\\n=== 等待STP收敛，请稍候... ===')",
        "    def wait_for_stp_convergence():",
        "        max_wait = 35",
        "        check_interval = 5",
        "        waited = 0",
        "        while waited < max_wait:",
        "            print(f'检查STP状态... (已等待{waited}秒)')",
        "            try:",
        "                has_flows = False",
        "                for switch_name, info in switches_info.items():",
        "                    response = requests.get(f'http://localhost:8081/stats/flow/{info[\"dpid\"]}', timeout=3)",
        "                    if response.status_code == 200:",
        "                        flows = response.json()",
        "                        if len(flows.get(str(info['dpid']), [])) > 0:",
        "                            has_flows = True",
        "                            break",
        "                if has_flows:",
        "                    print(f'检测到流表条目，STP可能已收敛 (等待了{waited}秒)')",
        "                    time.sleep(5)",
        "                    return waited + 5",
        "            except:",
        "                pass",
        "            time.sleep(check_interval)",
        "            waited += check_interval",
        "        print(f'达到最大等待时间{max_wait}秒')",
        "        return max_wait",
        "",
        "    actual_wait = wait_for_stp_convergence()",
        "    print(f'STP收敛等待完成！(实际等待: {actual_wait}秒)')",
        "else:",
        "    print('\\n[优化] 拓扑无环，跳过 STP 收敛等待')",
        "",
        "# 动态检查STP状态",
        "def check_stp_status():",
        "    print('\\n=== 检查STP状态 ===')",
        "    try:",
        "        for switch_name, info in switches_info.items():",
        "            dpid = info['dpid']",
        "            # 检查流表",
        "            response = requests.get(f'http://localhost:8081/stats/flow/{dpid}', timeout=5)",
        "            if response.status_code == 200:",
        "                flows = response.json()",
        "                flow_count = len(flows.get(str(dpid), []))",
        "                print(f'{switch_name}(DPID:{dpid})流表条目数: {flow_count}')",
        "            ",
        "            # 检查端口状态",
        "            response = requests.get(f'http://localhost:8081/stats/port/{dpid}', timeout=5)",
        "            if response.status_code == 200:",
        "                ports = response.json()",
        "                port_count = len(ports.get(str(dpid), []))",
        "                print(f'{switch_name}(DPID:{dpid})端口数: {port_count}')",
        "    except Exception as e:",
        "        print(f'无法获取STP状态: {e}')",
        "",
        "check_stp_status()",
        "",
        "# 动态添加ARP条目",
        "print('\\n=== 动态添加ARP条目 ===')",
        "def add_arp_entries():",
        "    # 为所有主机对添加ARP条目",
        "    from backend.utils.arp_utils import configure_static_arp",
        "    configure_static_arp(hosts_info)",

        # "    host_list = list(hosts_info.keys())",
        # "    for i, host1_name in enumerate(host_list):",
        # "        for host2_name in host_list[i+1:]:",
        # "            host1 = hosts_info[host1_name]['node']",
        # "            host2 = hosts_info[host2_name]['node']",
        # "            ",
        # "            # 互相添加ARP条目",
        # "            host1.cmd(f'arp -s {host2.IP()} {host2.MAC()}')",
        # "            host2.cmd(f'arp -s {host1.IP()} {host1.MAC()}')",
        "    ",
        # "    print(f'已为{len(host_list)}个主机添加ARP条目')",
        "",
        "add_arp_entries()",
        "",
        "# 动态测试连通性",
        "print('\\n=== 动态连通性测试 ===')",
        "def test_connectivity():",
        "    host_list = list(hosts_info.keys())",
        "    if len(host_list) >= 2:",
        "        # 测试第一个和最后一个主机",
        "        first_host_name = host_list[0]",
        "        last_host_name = host_list[-1]",
        "        ",
        "        first_host = hosts_info[first_host_name]['node']",
        "        last_host = hosts_info[last_host_name]['node']",
        "        ",
        "        print(f'测试 {first_host_name}({first_host.IP()}) -> {last_host_name}({last_host.IP()})')",
        "        ",
        "        # Mininet内置ping测试",
        "        result = net.ping([first_host, last_host])",
        "        print(f'Mininet ping结果: {result}% 丢包率')",
        "        ",
        "        # 详细的手动ping测试",
        "        print('\\n--- 详细ping测试 ---')",
        "        output = first_host.cmd(f'ping -c 3 -W 2 {last_host.IP()}')",
        "        print(f'{first_host_name} ping {last_host_name} 输出:\\n{output}')",
        "        ",
        "        # 反向ping测试",
        "        print('\\n--- 反向ping测试 ---')",
        "        output = last_host.cmd(f'ping -c 3 -W 2 {first_host.IP()}')",
        "        print(f'{last_host_name} ping {first_host_name} 输出:\\n{output}')",
        "        ",
        "        # 检查路由表",
        "        print('\\n--- 路由信息 ---')",
        "        print(f'{first_host_name}路由表: {first_host.cmd(\"ip route\").strip()}')",
        "        print(f'{last_host_name}路由表: {last_host.cmd(\"ip route\").strip()}')",
        "        ",
        "        # 检查ARP表",
        "        print('\\n--- ARP表 ---')",
        "        print(f'{first_host_name} ARP表: {first_host.cmd(\"arp -a\").strip()}')",
        "        print(f'{last_host_name} ARP表: {last_host.cmd(\"arp -a\").strip()}')",
        "    else:",
        "        print('主机数量不足，无法进行连通性测试')",
        "",
        "test_connectivity()",
        "",
        "# 全网ping测试",
        "print('\\n=== 全网连通性测试 ===')",
        "if len(hosts_info) > 1:",
        "    net.pingAll()",
        "else:",
        "    print('只有一个主机，跳过全网测试')",
        "",
        "# 提供进入CLI的选项",
        "print('\\n=== 测试完成 ===')",
        "print('如需进入交互模式，请取消下面一行的注释')",
        "# CLI(net)",
        "",
        "# 清理网络（如果不需要CLI）"
    ]

    return "\n".join(lines)