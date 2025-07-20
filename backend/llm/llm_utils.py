# backend/llm_utils.py

from openai import OpenAI
import json
from backend.llm.prompt_templates import PLANNER_SYSTEM_PROMPT

# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key="sk-692005762cca46ac9faf28703ae6efe0",
    base_url="https://api.deepseek.com"
)

# def call_llm_for_planning(intent_text: str) -> list[dict]:
#     prompt = f"用户意图如下：\n{intent_text}\n请根据上述意图输出结构化指令列表（JSON 数组）。"

#     # 调用 chat 接口
#     response = client.chat.completions.create(
#         model="deepseek-chat",
#         messages=[
#             {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.2
#     )

#     reply = response.choices[0].message.content

#     try:
#         return json.loads(reply)
#     except json.JSONDecodeError as e:
#         raise ValueError(f"❌ JSON 解析失败: {e}\n原始输出:\n{reply}")
