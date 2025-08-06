def configure_static_arp(hosts_info: dict):
    """
    为所有主机添加静态 ARP 条目。
    :param hosts_info: 结构为 { "h1": {"ip": "...", "node": Host对象}, ... }
    """
    host_list = list(hosts_info.keys())
    for i, h1_name in enumerate(host_list):
        for h2_name in host_list[i + 1:]:
            h1 = hosts_info[h1_name]["node"]
            h2 = hosts_info[h2_name]["node"]
            h1.cmd(f"arp -s {h2.IP()} {h2.MAC()}")
            h2.cmd(f"arp -s {h1.IP()} {h1.MAC()}")
    print(f"[ARP] 已为 {len(host_list)} 个主机配置静态 ARP 条目")


def print_arp_table(hosts_info: dict):
    """
    打印所有主机的 ARP 表（调试用）。
    :param hosts_info: 与上面相同的结构
    """
    print("\n[ARP] 所有主机当前 ARP 表：")
    for h_name, h_info in hosts_info.items():
        host = h_info["node"]
        output = host.cmd("arp -a")
        print(f"--- {h_name} ({h_info['ip']}) ---")
        print(output.strip())

def clear_arp_table(hosts_info: dict):
    """
    清空所有主机的 ARP 表，适用于需要重新学习或刷新 ARP 的场景。
    """
    print("\n[ARP] 正在清空所有主机的 ARP 表...")
    for h_name, h_info in hosts_info.items():
        host = h_info["node"]
        host.cmd("ip -s -s neigh flush all")
        print(f"[ARP] 已清空 {h_name} 的 ARP 表")


def get_arp_map(hosts_info: dict) -> dict:
    """
    获取所有主机当前 ARP 表，返回结构化字典：
    {
        "h1": [
            {"ip": "10.0.0.2", "mac": "00:00:00:00:00:02"},
            ...
        ],
        ...
    }
    """
    arp_result = {}
    for h_name, h_info in hosts_info.items():
        host = h_info["node"]
        raw_output = host.cmd("arp -n")
        entries = []
        for line in raw_output.strip().splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0].count('.') == 3:
                ip = parts[0]
                mac = parts[2]
                entries.append({"ip": ip, "mac": mac})
        arp_result[h_name] = entries
    return arp_result


def validate_arp_connectivity(hosts_info: dict, expected_peers: list = None) -> dict:
    """
    验证各主机是否具备所有其他主机的 ARP 表项。
    可指定 expected_peers 限制检查对象。
    
    返回格式：
    {
        "h1": {"missing": ["10.0.0.2", "10.0.0.3"]},
        "h2": {"missing": []},
        ...
    }
    """
    result = {}
    host_ips = {h: info["ip"] for h, info in hosts_info.items()}
    expected_ips = [ip for h, ip in host_ips.items() if not expected_peers or h in expected_peers]

    for h_name, h_info in hosts_info.items():
        host = h_info["node"]
        arp_table = host.cmd("arp -n")
        known_ips = set()
        for line in arp_table.strip().splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0].count('.') == 3:
                known_ips.add(parts[0])
        missing = [ip for ip in expected_ips if ip != h_info["ip"] and ip not in known_ips]
        result[h_name] = {"missing": missing}
    return result

