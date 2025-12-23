# backend/llm_utils.py

from openai import OpenAI
import json
import json
import re
# 初始化 DeepSeek 客户端
client = OpenAI(
    api_key="sk-692005762cca46ac9faf28703ae6efe0",
    base_url="https://api.deepseek.com"
)
# client = OpenAI(
#     api_key="ollama",  # 随便写，Ollama 不校验
#     base_url="http://localhost:11434/v1"
# )




def extract_pure_json(llm_output: str):
    """
    从本地 LLM（如 deepseek-r1）输出中提取纯 JSON
    - 去除 <think>...</think>
    - 去除 ```json ... ``` / ``` ... ```
    - 抽取完整 JSON 对象或数组
    - 返回 Python dict 或 list
    """
    if not llm_output or not llm_output.strip():
        raise ValueError("LLM output is empty")

    text = llm_output.strip()

    # 1️⃣ 删除 <think>...</think>
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # 2️⃣ 删除 ```json ... ``` 或 ``` ... ```
    fence_match = re.search(
        r"```(?:json)?\s*([\s\S]*?)\s*```",
        text,
        flags=re.IGNORECASE
    )
    if fence_match:
        text = fence_match.group(1).strip()

    # 3️⃣ 找到 JSON 起始符
    json_start = min(
        [i for i in (text.find('{'), text.find('[')) if i != -1],
        default=-1
    )
    if json_start == -1:
        raise ValueError(f"No JSON found in LLM output:\n{text}")

    text = text[json_start:].strip()

    # 4️⃣ 提取括号平衡的 JSON（防止后面还有垃圾）
    def extract_balanced_json(s: str) -> str:
        stack = []
        in_string = False
        escape = False

        for i, ch in enumerate(s):
            if in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            else:
                if ch == '"':
                    in_string = True
                    continue
                if ch in '{[':
                    stack.append(ch)
                elif ch in '}]':
                    if not stack:
                        break
                    left = stack.pop()
                    if (left == '{' and ch != '}') or (left == '[' and ch != ']'):
                        raise ValueError("Mismatched JSON brackets")
                    if not stack:
                        return s[:i + 1]

        raise ValueError("Unbalanced JSON in LLM output")

    json_str = extract_balanced_json(text)

    # 5️⃣ 解析 JSON
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON decode failed: {e}\nExtracted JSON:\n{json_str}")


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
