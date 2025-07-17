import requests
import json
RYU_REST_API = "http://localhost:8081"

def send_flow_mod(flow_rule: dict) -> bool:
    try:
        url = f"{RYU_REST_API}/stats/flowentry/add"
        payload = {
             "dpid": flow_rule["dpid"],
             "priority": flow_rule["priority"],
             "match": flow_rule["match"],
             "actions": flow_rule["actions"],
             "command": "add"
        }
 
        response = requests.post(url, json=payload)
 
        print("[DEBUG] 请求 URL:", url)
        print("[DEBUG] 请求 Payload:", json.dumps(payload, indent=2))
        print("[DEBUG] 响应状态码:", response.status_code)
        print("[DEBUG] 响应内容:", response.text)
 
        return response.status_code == 200
 
    except Exception as e:
        print(f"Ryu API调用失败: {e}")
        return False


