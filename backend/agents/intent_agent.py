from openai import OpenAI
import json

client = OpenAI(api_key="sk-692005762cca46ac9faf28703ae6efe0", base_url="https://api.deepseek.com")

class IntentAgent:
    def __init__(self):
        pass

    def intent_to_instruction(self, intent_text: str) -> dict:
        prompt = f"""
你是一个精通网络仿真的工程师助手，专门使用 Mininet 和 Ryu 控制器。

请将以下用户网络意图，解析成一个严格的 JSON 指令，结构如下：

{{
  "action": "<操作类型，如 create_topology, delete_host, ping_test, deny_access 等>",
  "hosts": [主机名称列表],
  "switches": [交换机名称列表],
  "links": [{{"src": "<节点1>", "dst": "<节点2>"}}，...],
  "controller": {{
    "type": "RemoteController",
    "ip": "127.0.0.1",
    "port": 6633
  }},
  "extra": {{其他需要的参数，比如ping目标、访问控制规则等}}
}}

只返回符合 JSON 格式的字符串，不要多余解释和代码，也不要 Markdown 格式。

用户意图：
{intent_text}
"""
        messages = [
            {"role": "system", "content": "你是网络拓扑与控制指令生成助手，只输出JSON指令。"},
            {"role": "user", "content": prompt}
        ]

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        content = response.choices[0].message.content.strip()
        print("LLM 返回原始内容:\n", content)
        # 清除 markdown 格式包裹
        if content.startswith("```"):
            content = content.strip("`")
            lines = content.splitlines()
            if lines and lines[0].startswith("json"):
                content = "\n".join(lines[1:])  # 删除第一行 ```json

        print("LLM 返回清洗后内容:\n", content)

        if not content:
            raise Exception("LLM 返回为空，请检查提示词")

        

        # 尝试解析JSON，如果失败，抛异常提醒调试
        try:
            json_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise Exception(f"LLM 返回内容不是有效JSON: {e}\n内容:\n{content}")

        return json_data
