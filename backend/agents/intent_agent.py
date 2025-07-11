from openai import OpenAI
import json

client = OpenAI(api_key="sk-692005762cca46ac9faf28703ae6efe0", base_url="https://api.deepseek.com")

class IntentAgent:
    def __init__(self):
        pass

    def intent_to_instruction(self, intent_text: str) -> dict:
        prompt = f"""
你是一个 SDN 网络专家，请根据用户输入的意图，提取并返回结构化指令（JSON格式），以便后端执行。

输出要求：
- 仅输出纯 JSON（不要包含任何markdown标记或解释说明）。
- 可用字段包括：
  action: create_topology | install_flowtable | ping_test
  hosts: ["h1", "h2"]
  switches: ["s1"]
  links: [{{"src": "h1", "dst": "s1"}}]
  controller: {{
    "type": "RemoteController",
    "ip": "127.0.0.1",
    "port": 6633
  }}
  extra: 
    对于 install_flowtable，需要包含:
      - match: {{"nw_src": "IP1", "nw_dst": "IP2"}}  # 匹配规则
      - actions: "DENY" | "ALLOW"  # 动作类型
      - priority: 数字  # 流表优先级
    对于 ping_test，extra 字段中必须包含 source（主机名）和 target（目标主机的 IP 地址，例如 10.0.0.1），不要使用主机名。

注意：
- 注意：所有数值必须是十进制，禁止出现 0x0800 这样的十六进制形式，否则会解析失败。

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
        # print("LLM 返回原始内容:\n", content)

        # 清除 markdown 格式包裹
        if content.startswith("```"):
            content = content.strip("`")
            lines = content.splitlines()
            if lines and lines[0].startswith("json"):
                content = "\n".join(lines[1:])  # 删除第一行 ```json

        print("LLM 返回清洗Markdown后内容:\n", content)

        if not content:
            raise Exception("LLM 返回为空，请检查提示词")

        # 尝试解析JSON，如果失败，抛异常提醒调试
        try:
            json_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise Exception(f"LLM 返回内容不是有效JSON: {e}\n内容:\n{content}")

        return json_data
