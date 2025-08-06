from openai import OpenAI
import json
import os
import uuid
import time

from backend.utils.token_utils import record_tokens_from_response
from backend.utils.messagepool_utils import send_intent

client = OpenAI(api_key="sk-692005762cca46ac9faf28703ae6efe0",
                base_url="https://api.deepseek.com")


class IntentAgent:
    def __init__(self, prompt_path="/data/gjw/Meta-IBN/backend/agents/prompts/intent_agent.txt"):
        self.prompt_path = prompt_path
        self.name = "IntentAgent"

    def load_prompt_template(self) -> str:
        """
        从本地文本文件加载提示词模板
        """
        if not os.path.exists(self.prompt_path):
            raise FileNotFoundError(f"提示词文件不存在: {self.prompt_path}")
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def build_prompt(self, intent_text: str) -> str:
        """
        替换模板中的 {intent_text} 变量
        """
        template = self.load_prompt_template()
        return template.format(intent_text=intent_text)

    def intent_to_instruction(self, intent_text: str) -> list[dict]:
        """
        将用户意图转换为结构化指令列表（不负责发送）
        """
        response = None
        prompt = self.build_prompt(intent_text)
        messages = [
            {"role": "system", "content": "你是网络拓扑与控制指令生成助手，只输出JSON指令。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature = 0.0,
                stream=False
            )
            content = response.choices[0].message.content.strip()
        except Exception as e:
            raise Exception(f"LLM 请求失败: {e}")

        if response:
            record_tokens_from_response(response)
        else:
            raise Exception("LLM 响应为空，无法继续解析")

        # 清除 markdown 包裹
        if content.startswith("```"):
            content = content.strip("`")
            lines = content.splitlines()
            if lines and lines[0].startswith("json"):
                content = "\n".join(lines[1:])  # 删除第一行 ```json

        print("[IntentAgent] 🔄 LLM 返回清洗后的内容:\n", content)

        if not content:
            raise Exception("LLM 返回为空，请检查提示词")

        try:
            json_data = json.loads(content)
            if isinstance(json_data, dict):
                return [json_data]
            elif isinstance(json_data, list):
                return json_data
            else:
                raise Exception("返回内容既不是 JSON 对象也不是数组")
        except json.JSONDecodeError as e:
            raise Exception(f"LLM 返回内容不是有效JSON: {e}\n内容:\n{content}")
    
    def send_instruction(self, intent_text: str):
        try:
            instructions = self.intent_to_instruction(intent_text)
        except Exception as e:
            print(f"[IntentAgent] ❌ 指令解析失败: {e}")
            return

        trace_id = str(uuid.uuid4())
        print(f"[IntentAgent] ✅ 拆解为 {len(instructions)} 条指令，trace_id={trace_id}")

        for instr in instructions:
            send_intent(instr, sender="IntentAgent", trace_id=trace_id)  # ✅ 统一传入 trace_id

