# utils/utils.py
import networkx as nx

def convert_switch_name_to_dpid(name: str) -> int:
    """
    将交换机名（如 's1'）转换为 Ryu 需要的 dpid 整数（如 1）
    """
    try:
        if name.lower().startswith("s"):
            return int(name[1:])
        raise ValueError
    except Exception:
        raise ValueError(f"交换机名称不合法: {name}")



def is_cyclic_topology(links: list) -> bool:
    """
    判断拓扑链路是否构成环路结构。
    如果存在环路，返回 True；否则返回 False。
    """
    G = nx.Graph()
    for link in links:
        src = link.get("src")
        dst = link.get("dst")
        if src and dst:
            G.add_edge(src, dst)
    return not nx.is_tree(G)  # 非树即有环
