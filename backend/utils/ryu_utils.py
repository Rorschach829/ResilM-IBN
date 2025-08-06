import requests

def get_all_switch_ids():
    try:
        resp = requests.get("http://localhost:8081/stats/switches")
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print("[ERROR] 获取交换机列表失败:", e)
    return []


