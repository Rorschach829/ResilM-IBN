# utils/utils.py

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
