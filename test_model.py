from openai import OpenAI

# 1️⃣ 创建 client，指向 Ollama 的 OpenAI 兼容接口
client = OpenAI(
    api_key="ollama",  # 随便写，Ollama 不校验
    base_url="http://localhost:11434/v1"
)

# 2️⃣ 发一个最简单的对话请求
#可直接输出token
# response = client.chat.completions.create(
#     model="phi4:14b",   # ⚠️ 一定要和 ollama list 里的名字一致
#     messages=[
#         {"role": "system", "content": "你是一个严谨的工程师助手"},
#         {"role": "user", "content": "请用一句话解释什么是意图驱动网络"}
#     ],
#     temperature=0.0,
#     stream=False
# )

# response = client.chat.completions.create(
#     model="phi3:medium",   # ⚠️ 一定要和 ollama list 里的名字一致
#     messages=[
#         {"role": "system", "content": "你是一个严谨的工程师助手"},
#         {"role": "user", "content": "请用一句话解释什么是意图驱动网络"}
#     ],
#     temperature=0.0,
#     stream=False
# )

# response = client.chat.completions.create(
#     model="qwen2.5-coder:32b",   # ⚠️ 一定要和 ollama list 里的名字一致
#     messages=[
#         {"role": "system", "content": "你是一个严谨的工程师助手"},
#         {"role": "user", "content": "请用一句话解释什么是意图驱动网络"}
#     ],
#     temperature=0.0,
#     stream=False
# )

# response = client.chat.completions.create(
#     model="codellama:70b",   # ⚠️ 一定要和 ollama list 里的名字一致
#     messages=[
#         {"role": "system", "content": "你是一个严谨的工程师助手"},
#         {"role": "user", "content": "请用一句话解释什么是意图驱动网络"}
#     ],
#     temperature=0.0,
#     stream=False
# )

# response = client.chat.completions.create(
#     model="mistral-small:24b",   # ⚠️ 一定要和 ollama list 里的名字一致
#     messages=[
#         {"role": "system", "content": "你是一个严谨的工程师助手"},
#         {"role": "user", "content": "请用一句话解释什么是意图驱动网络"}
#     ],
#     temperature=0.0,
#     stream=False
# )

# response = client.chat.completions.create(
#     model="llama3.1:latest",   # ⚠️ 一定要和 ollama list 里的名字一致
#     messages=[
#         {"role": "system", "content": "你是一个严谨的工程师助手"},
#         {"role": "user", "content": "请用一句话解释什么是意图驱动网络"}
#     ],
#     temperature=0.0,
#     stream=False
# )

response = client.chat.completions.create(
    model="deepseek-r1:32b",   # ⚠️ 一定要和 ollama list 里的名字一致
    messages=[
        {"role": "system", "content": "你是一个严谨的工程师助手"},
        {"role": "user", "content": "请用一句话解释什么是意图驱动网络"}
    ],
    temperature=0.0,
    stream=False
)

# 3️⃣ 打印结果
print("====== 模型回复 ======")
print(response.choices[0].message.content)

# 4️⃣ 看看有没有 token usage（可能没有，这是正常的）
print("\n====== usage ======")
print(getattr(response, "usage", None))