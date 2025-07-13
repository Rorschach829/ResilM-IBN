# backend/utils/topology_utils.py

import time
import requests

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
