from openai import OpenAI
import json
import os
import uuid
import time
from backend.utils import token_counter
from backend.llm.llm_utils import client
from backend.llm.llm_utils import extract_pure_json
from backend.utils.token_utils import record_tokens_from_response
from backend.utils.messagepool_utils import send_intent

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
            {"role": "system", "content": "你是网络拓扑与控制指令生成助手，必须只输出严格JSON（对象或数组），禁止输出<think>、解释文字、Markdown代码块。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = client.chat.completions.create(
                model="qwen-plus",
                # model="deepseek-chat",
                messages=messages,
                temperature = 0.0,
                stream=False
            )
            content = response.choices[0].message.content.strip()
            print("[IntentAgent] LLM 返回初始内容:\n", content)
        except Exception as e:
            raise Exception(f"LLM 请求失败: {e}")
        
        #记录token
        # resp = ...
        t = getattr(getattr(response, "usage", None), "total_tokens", 0) or 0
        token_counter.add_intent(t)

        if response:
            print("本次调用intent_agent的token使用量如下")
            record_tokens_from_response(response)
        else:
            raise Exception("LLM 响应为空，无法继续解析")

        data = extract_pure_json(content)   # ✅ data 是 dict 或 list
        print("[IntentAgent] 🔄 LLM 返回清洗后的 JSON 对象:\n", data)

        # 统一 action（强烈建议，防止 plan_Steps 这种）
        print("[DEBUG] data type before norm:", type(data), data)
        def norm_action(x):
            print("[DEBUG] norm_action x type:", type(x), "action type:", type(x.get("action")) if isinstance(x, dict) else None)
            if isinstance(x, dict) and "action" in x and isinstance(x["action"], str):
                x["action"] = x["action"].strip().lower()
            return x
        # def norm_action(x):
        #     if isinstance(x, dict) and "action" in x and isinstance(x["action"], str):
        #         x["action"] = x["action"].strip().lower()
        #     return x

        if isinstance(data, dict):
            data = norm_action(data)
            return [data]
        elif isinstance(data, list):
            return [norm_action(item) if isinstance(item, dict) else item for item in data]
        else:
            raise Exception("返回内容既不是 JSON 对象也不是数组")
        # 清除 markdown 包裹
        # if content.startswith("```"):
        #     content = content.strip("`")
        #     lines = content.splitlines()
        #     if lines and lines[0].startswith("json"):
        #         content = "\n".join(lines[1:])  # 删除第一行 ```json

        # print("[IntentAgent] 🔄 LLM 返回清洗后的内容:\n", content)

        # if not content:
        #     raise Exception("LLM 返回为空，请检查提示词")

        # try:
        #     json_data = json.loads(content)
        #     print("json_data的格式为：")
        #     print(type(json_data))
        #     print("json_data的数据为")
        #     print(json_data)
        #     if isinstance(json_data, dict):
        #         return [json_data]
        #     elif isinstance(json_data, list):
        #         return json_data
        #     else:
        #         raise Exception("返回内容既不是 JSON 对象也不是数组")
        # except json.JSONDecodeError as e:
        #     raise Exception(f"LLM 返回内容不是有效JSON: {e}\n内容:\n{content}")
    
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

