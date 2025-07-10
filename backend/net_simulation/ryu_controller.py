import requests

RYU_REST_API = "http://localhost:8080"

def send_flow_mod(flow_rule: dict):
    # 这里用REST API调用Ryu控制器，示例代码
    url = f"{RYU_REST_API}/stats/flowentry/add"
    response = requests.post(url, json=flow_rule)
    return response.status_code == 200
