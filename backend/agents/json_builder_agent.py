from backend.llm.llm_utils import client, extract_pure_json
from backend.utils.messagepool_utils import send_intent
from backend.coordinator.message_pool import message_pool
from backend.utils import token_counter
from backend.utils.token_utils import record_tokens_from_response
import requests
import re
from typing import List, Optional


class JSONBuilderAgent:
    def __init__(self):
        self.name = "JSONBuilderAgent"
        message_pool.subscribe("plan_steps", self.handle_plan)

    # ✅ 修正：加 self
    def load_json_builder_prompt(self) -> str:
        with open("/data/gjw/Meta-IBN/backend/agents/prompts/json_builder_agent.txt", "r", encoding="utf-8") as f:
            return f.read()

    def handle_plan(self, message: dict):
        steps = message.get("steps", [])
        intent_text = message.get("intent_text", "")

        assert "trace_id" in message, "[JSONBuilderAgent] ❌ 缺少 trace_id"
        trace_id = message["trace_id"]

        print(f"[JSONBuilderAgent] ✅ 批处理 {len(steps)} 条步骤，trace_id={trace_id}")

        # === 跳过拓扑创建步骤，如果当前拓扑已存在 ===
        try:
            resp = requests.get("http://localhost:5000/topology", timeout=2)
            topo = resp.json()
            if len(topo.get("nodes", [])) > 0:
                print("[JSONBuilderAgent] ✅ 当前拓扑非空，跳过拓扑创建步骤")
                steps = [s for s in steps if not ("创建" in s and "拓扑" in s)]
        except Exception as e:
            print(f"[JSONBuilderAgent] ⚠️ 无法访问拓扑接口，保留所有步骤: {e}")

        # === 自动注入路径信息上下文 ===
        extra_context = None
        host_matches = re.findall(r'\bh\d+\b', intent_text)
        if len(host_matches) >= 2:
            h1, h2 = host_matches[0], host_matches[1]
            try:
                resp = requests.get(f"http://localhost:5000/shortest_path?src={h1}&dst={h2}", timeout=2)
                data = resp.json()
                path = data.get("path", [])
                if path:
                    extra_context = f"{h1} 与 {h2} 之间的网络路径为：{' -> '.join(path)}。请根据此路径操作对应交换机上的流表。"
                    print(f"[JSONBuilderAgent] ✅ 注入路径上下文: {extra_context}")
            except Exception as e:
                print(f"[JSONBuilderAgent] ⚠️ 查询 shortest_path 接口失败: {e}")

        # === 构建 Prompt（原逻辑不动） ===
        prompt = self.build_batch_prompt(steps, extra_context=extra_context)

        # ✅ 关键：把你长规则 prompt 用上
        json_prompt = self.load_json_builder_prompt()

        messages = [
            {"role": "system", "content": "你是网络拓扑与控制指令生成助手，必须只输出严格JSON（对象或数组），禁止输出<think>、解释文字、Markdown代码块。"},
            # ✅ 修正：把 json_prompt + prompt 拼进去（否则模型根本看不到你的规则）
            {"role": "user", "content": f"{json_prompt}\n\n{prompt}"}
        ]

        try:
            response = client.chat.completions.create(
                # model="qwen-plus",
                # model="deepseek-chat",
                model="glm-4.6",
                # model="kimi-k2-thinking",
                extra_body={"enable_thinking": False},
                messages=messages,
                stream=False,
                temperature=0.0
            )

            raw = response.choices[0].message.content.strip()
            # print(f"[JSONBuilderAgent] 📥 LLM 原始输出:\n{raw}")

            parsed = extract_pure_json(raw)
            # print(f"[JSONBuilderAgent] 📥 LLM 清洗后的输出:\n{parsed}")

            # ✅ parsed 已经是 list 或 dict，不要 json.loads
            if isinstance(parsed, dict):
                json_array = [parsed]
            elif isinstance(parsed, list):
                json_array = parsed
            else:
                raise ValueError(f"Unexpected type from extract_pure_json: {type(parsed)}")

        except Exception as e:
            print(f"[JSONBuilderAgent] ❌ LLM 调用或 JSON 解析失败: {e}")
            return

        #记录json_tokens
        t = getattr(getattr(response, "usage", None), "total_tokens", 0) or 0
        token_counter.add_json(t)
        
        # token 统计（原逻辑不动）
        if response:
            print("本次JSON_builder_agent调用llm的token使用量如下")
            record_tokens_from_response(response)
        else:
            raise Exception("LLM 响应为空，无法继续解析")

        if not isinstance(json_array, list):
            print("[JSONBuilderAgent] ❌ 返回结果不是 JSON 数组")
            return

        # === 分发（原逻辑不动） ===
        for i, instr in enumerate(json_array):
            # ✅ 稳一点：只处理 dict
            if not isinstance(instr, dict):
                print(f"[JSONBuilderAgent] ⚠️ 指令不是 dict，跳过: {instr}")
                continue

            # ✅ action 规范化（防 plan_Steps）
            if isinstance(instr.get("action"), str):
                instr["action"] = instr["action"].strip().lower()

            instr["trace_id"] = trace_id
            instr["intent_text"] = intent_text

            if i == len(json_array) - 1:
                instr["final_step"] = True

            print(f"[JSONBuilderAgent] 📤 发送指令: {instr.get('action')} trace_id={trace_id}")
            send_intent(instr, sender="JSONBuilderAgent", trace_id=trace_id)

    def build_batch_prompt(self, steps: List[str], extra_context: Optional[str] = None) -> str:
        prompt_lines = []
        if extra_context:
            prompt_lines.append(f"[上下文信息]\n{extra_context}\n")

        prompt_lines.append("[用户意图步骤]")
        for step in steps:
            prompt_lines.append(step)
        prompt_lines.append("\n请根据以上步骤，生成对应的结构化 JSON 指令数组。")

        return "\n".join(prompt_lines)





#一步生成错误版
# from backend.llm.prompt_templates import load_json_builder_prompt
# from backend.llm.llm_utils import client
# from backend.llm.llm_utils import extract_pure_json
# from backend.llm.llm_utils import extract_pure_json
# from backend.utils.utils import extract_json_from_response
# from backend.utils.messagepool_utils import send_intent
# from backend.coordinator.message_pool import message_pool
# from backend.utils.token_utils import record_tokens_from_response
# import uuid, json, requests
# import re
# from typing import List, Optional


# class JSONBuilderAgent:
#     def __init__(self):
#         self.name = "JSONBuilderAgent"
#         message_pool.subscribe("plan_steps", self.handle_plan)

#     def load_json_builder_prompt() -> str:
#         with open("/data/gjw/Meta-IBN/backend/agents/prompts/json_builder_agent.txt", "r", encoding="utf-8") as f:
#             return f.read()

#     def handle_plan(self, message: dict):
#         steps = message.get("steps", [])
#         intent_text = message.get("intent_text", "")

#         assert "trace_id" in message, "[JSONBuilderAgent] ❌ 缺少 trace_id"
#         trace_id = message["trace_id"]

#         print(f"[JSONBuilderAgent] ✅ 批处理 {len(steps)} 条步骤，trace_id={trace_id}")

#         # === 跳过拓扑创建步骤，如果当前拓扑已存在 ===
#         try:
#             resp = requests.get("http://localhost:5000/topology", timeout=2)
#             topo = resp.json()
#             if len(topo.get("nodes", [])) > 0:
#                 print("[JSONBuilderAgent] ✅ 当前拓扑非空，跳过拓扑创建步骤")
#                 steps = [
#                     s for s in steps
#                     if not ("创建" in s and "拓扑" in s)
#                 ]
#         except Exception as e:
#             print(f"[JSONBuilderAgent] ⚠️ 无法访问拓扑接口，保留所有步骤: {e}")

#         # === 自动注入路径信息上下文 ===
#         extra_context = None
#         host_matches = re.findall(r'\bh\d+\b', intent_text)
#         if len(host_matches) >= 2:
#             h1, h2 = host_matches[0], host_matches[1]
#             try:
#                 resp = requests.get(f"http://localhost:5000/shortest_path?src={h1}&dst={h2}", timeout=2)
#                 data = resp.json()
#                 path = data.get("path", [])
#                 if path:
#                     extra_context = f"{h1} 与 {h2} 之间的网络路径为：{' -> '.join(path)}。请根据此路径操作对应交换机上的流表。"
#                     print(f"[JSONBuilderAgent] ✅ 注入路径上下文: {extra_context}")
#             except Exception as e:
#                 print(f"[JSONBuilderAgent] ⚠️ 查询 shortest_path 接口失败: {e}")

#         # === 构建 Prompt ===
#         prompt = self.build_batch_prompt(steps, extra_context=extra_context)

#         json_prompt = self.load_json_builder_prompt()
#         messages = [
#             {"role": "system", "content": "你是网络拓扑与控制指令生成助手，必须只输出严格JSON（对象或数组），禁止输出<think>、解释文字、Markdown代码块。"},
#             {"role": "user", "content": prompt}
#         ]

#         try:
#             response = client.chat.completions.create(
#                 model="qwen-plus",
#                 # model="deepseek-chat",
#                 # model="phi4:14b",
#                 # model="phi3:medium",
#                 # model="qwen2.5-coder:32b",
#                 # model="codellama:70b",
#                 # model="mistral-small:24b",
#                 # model="llama3.1:latest",
#                 # model="deepseek-r1:32b",
#                 # model="deepseek-r1:70b",
#                 messages=messages,
#                 stream=False,
#                 temperature=0.0
#             )
#             content = response.choices[0].message.content.strip()
#             print(f"[JSONBuilderAgent] 📥 LLM 原始输出:\n{content}")

#             content = extract_pure_json(content)
#             print(f"[JSONBuilderAgent] 📥 LLM 清洗后的输出:\n{content}")
#             # ✅ content 已经是 list 或 dict，不需要 json.loads
#             if isinstance(content, dict):
#                 json_array = [content]
#             elif isinstance(content, list):
#                 json_array = content
#             else:
#                 raise ValueError(f"Unexpected type from extract_pure_json: {type(content)}")
#             # json_array = json.loads(content)
#         except Exception as e:
#             print(f"[JSONBuilderAgent] ❌ LLM 调用或 JSON 解析失败: {e}")
#             return

#         if response:
#             print("本次JSON_builder_agent调用llm的token使用量如下")
#             record_tokens_from_response(response)
#         else:
#             raise Exception("LLM 响应为空，无法继续解析")

#         if not isinstance(json_array, list):
#             print("[JSONBuilderAgent] ❌ 返回结果不是 JSON 数组")
#             return

#         for i, instr in enumerate(json_array):
#             instr["trace_id"] = trace_id
#             instr["intent_text"] = intent_text

#             if i == len(json_array) - 1:
#                 instr["final_step"] = True  # ✅ 给最后一条指令标记

#             print(f"[JSONBuilderAgent] 📤 发送指令: {instr.get('action')} trace_id={trace_id}")
#             send_intent(instr, sender="JSONBuilderAgent", trace_id=trace_id)

#     def build_batch_prompt(self, steps: List[str], extra_context: Optional[str] = None) -> str:
#         prompt_lines = []
#         if extra_context:
#             prompt_lines.append(f"[上下文信息]\n{extra_context}\n")

#         prompt_lines.append("[用户意图步骤]")
#         for i, step in enumerate(steps, 1):
#             prompt_lines.append(f"{step}")
#         prompt_lines.append("\n请根据以上步骤，生成对应的结构化 JSON 指令数组。")

#         return "\n".join(prompt_lines)




#逐步生成json
# from backend.llm.llm_utils import client, extract_pure_json
# from backend.utils.messagepool_utils import send_intent
# from backend.coordinator.message_pool import message_pool
# from backend.utils.token_utils import record_tokens_from_response
# import requests, re
# from typing import List, Optional


# class JSONBuilderAgent:
#     def __init__(self):
#         self.name = "JSONBuilderAgent"
#         message_pool.subscribe("plan_steps", self.handle_plan)

#     def load_json_builder_prompt(self) -> str:
#         with open("/data/gjw/Meta-IBN/backend/agents/prompts/json_builder_agent.txt", "r", encoding="utf-8") as f:
#             return f.read()

#     def handle_plan(self, message: dict):
#         steps = message.get("steps", [])
#         intent_text = message.get("intent_text", "")

#         assert "trace_id" in message, "[JSONBuilderAgent] ❌ 缺少 trace_id"
#         trace_id = message["trace_id"]

#         print(f"[JSONBuilderAgent] ✅ 批处理 {len(steps)} 条步骤，trace_id={trace_id}")

#         # === 跳过拓扑创建步骤，如果当前拓扑已存在 ===
#         try:
#             resp = requests.get("http://localhost:5000/topology", timeout=2)
#             topo = resp.json()
#             if len(topo.get("nodes", [])) > 0:
#                 print("[JSONBuilderAgent] ✅ 当前拓扑非空，跳过拓扑创建步骤")
#                 steps = [s for s in steps if not ("创建" in s and "拓扑" in s)]
#         except Exception as e:
#             print(f"[JSONBuilderAgent] ⚠️ 无法访问拓扑接口，保留所有步骤: {e}")

#         # === 自动注入路径信息上下文 ===
#         extra_context = None
#         host_matches = re.findall(r'\bh\d+\b', intent_text)
#         if len(host_matches) >= 2:
#             h1, h2 = host_matches[0], host_matches[1]
#             try:
#                 resp = requests.get(f"http://localhost:5000/shortest_path?src={h1}&dst={h2}", timeout=2)
#                 data = resp.json()
#                 path = data.get("path", [])
#                 if path:
#                     extra_context = f"{h1} 与 {h2} 之间的网络路径为：{' -> '.join(path)}。请根据此路径操作对应交换机上的流表。"
#                     print(f"[JSONBuilderAgent] ✅ 注入路径上下文: {extra_context}")
#             except Exception as e:
#                 print(f"[JSONBuilderAgent] ⚠️ 查询 shortest_path 接口失败: {e}")

#         # === 构建 Prompt（你的原逻辑不动） ===
#         prompt = self.build_batch_prompt(steps, extra_context=extra_context)

#         # ✅ 关键：把你长规则 prompt 用上（否则模型看不到）
#         json_prompt = self.load_json_builder_prompt()

#         messages = [
#             # system 给短硬约束（可选）
#             {"role": "system", "content": "你是网络拓扑与控制指令生成助手，必须只输出严格JSON（对象或数组），禁止输出<think>、解释文字、Markdown代码块。"},
#             # user 把“长规则 + 本次步骤”拼在一起（推荐本地模型）
#             {"role": "user", "content": f"{json_prompt}\n\n{prompt}"}
#         ]

#         try:
#             response = client.chat.completions.create(
#                 model="deepseek-chat",
#                 # model="phi4:14b",
#                 # model="phi3:medium",
#                 # model="qwen2.5-coder:32b",
#                 # model="codellama:70b",
#                 # model="mistral-small:24b",
#                 # model="llama3.1:latest",
#                 # model="deepseek-r1:32b",
#                 # model="deepseek-r1:70b",
#                 messages=messages,
#                 stream=False,
#                 temperature=0.0
#             )

#             raw = response.choices[0].message.content.strip()
#             print(f"[JSONBuilderAgent] 📥 LLM 原始输出:\n{raw}")

#             parsed = extract_pure_json(raw)
#             print(f"[JSONBuilderAgent] 📥 LLM 清洗后的输出:\n{parsed}")

#             # ✅ parsed 已经是 list 或 dict，不要 json.loads
#             if isinstance(parsed, dict):
#                 json_array = [parsed]
#             elif isinstance(parsed, list):
#                 json_array = parsed
#             else:
#                 raise ValueError(f"Unexpected type from extract_pure_json: {type(parsed)}")

#         except Exception as e:
#             print(f"[JSONBuilderAgent] ❌ LLM 调用或 JSON 解析失败: {e}")
#             return

#         print("本次JSON_builder_agent调用llm的token使用量如下")
#         record_tokens_from_response(response)

#         if not isinstance(json_array, list):
#             print("[JSONBuilderAgent] ❌ 返回结果不是 JSON 数组")
#             return

#         for i, instr in enumerate(json_array):
#             if not isinstance(instr, dict):
#                 print(f"[JSONBuilderAgent] ⚠️ 指令不是 dict，跳过: {instr}")
#                 continue

#             # ✅ action 兜底规范化，防止 plan_Steps
#             if isinstance(instr.get("action"), str):
#                 instr["action"] = instr["action"].strip().lower()

#             instr["trace_id"] = trace_id
#             instr["intent_text"] = intent_text

#             if i == len(json_array) - 1:
#                 instr["final_step"] = True

#             print(f"[JSONBuilderAgent] 📤 发送指令: {instr.get('action')} trace_id={trace_id}")
#             send_intent(instr, sender="JSONBuilderAgent", trace_id=trace_id)

#     def build_batch_prompt(self, steps: List[str], extra_context: Optional[str] = None) -> str:
#         prompt_lines = []
#         if extra_context:
#             prompt_lines.append(f"[上下文信息]\n{extra_context}\n")

#         prompt_lines.append("[用户意图步骤]")
#         for step in steps:
#             prompt_lines.append(step)
#         prompt_lines.append("\n请根据以上步骤，生成对应的结构化 JSON 指令数组。")

#         return "\n".join(prompt_lines)
# from backend.llm.llm_utils import client, extract_pure_json
# from backend.utils.messagepool_utils import send_intent
# from backend.coordinator.message_pool import message_pool
# from backend.utils.token_utils import record_tokens_from_response
# import requests, re
# from typing import List, Optional


# class JSONBuilderAgent:
#     def __init__(self):
#         self.name = "JSONBuilderAgent"
#         message_pool.subscribe("plan_steps", self.handle_plan)

#     def load_json_builder_prompt(self) -> str:
#         with open("/data/gjw/Meta-IBN/backend/agents/prompts/json_builder_agent.txt", "r", encoding="utf-8") as f:
#             return f.read()

#     # ✅ 新增：构建“单个 step”的 prompt（保留你原 prompt 风格）
#     def build_step_prompt(self, step: str, extra_context: Optional[str] = None) -> str:
#         prompt_lines = []
#         if extra_context:
#             prompt_lines.append(f"[上下文信息]\n{extra_context}\n")

#         prompt_lines.append("[用户意图步骤]")
#         prompt_lines.append(step)
#         prompt_lines.append("\n请仅针对以上这一步，生成对应的结构化 JSON 指令（对象或数组）。")

#         return "\n".join(prompt_lines)

#     def handle_plan(self, message: dict):
#         steps = message.get("steps", [])
#         intent_text = message.get("intent_text", "")

#         assert "trace_id" in message, "[JSONBuilderAgent] ❌ 缺少 trace_id"
#         trace_id = message["trace_id"]

#         print(f"[JSONBuilderAgent] ✅ 批处理 {len(steps)} 条步骤，trace_id={trace_id}")

#         # === 跳过拓扑创建步骤，如果当前拓扑已存在 ===
#         try:
#             resp = requests.get("http://localhost:5000/topology", timeout=2)
#             topo = resp.json()
#             if len(topo.get("nodes", [])) > 0:
#                 print("[JSONBuilderAgent] ✅ 当前拓扑非空，跳过拓扑创建步骤")
#                 steps = [s for s in steps if not ("创建" in s and "拓扑" in s)]
#         except Exception as e:
#             print(f"[JSONBuilderAgent] ⚠️ 无法访问拓扑接口，保留所有步骤: {e}")

#         # === 自动注入路径信息上下文 ===
#         extra_context = None
#         host_matches = re.findall(r'\bh\d+\b', intent_text)
#         if len(host_matches) >= 2:
#             h1, h2 = host_matches[0], host_matches[1]
#             try:
#                 resp = requests.get(f"http://localhost:5000/shortest_path?src={h1}&dst={h2}", timeout=2)
#                 data = resp.json()
#                 path = data.get("path", [])
#                 if path:
#                     extra_context = f"{h1} 与 {h2} 之间的网络路径为：{' -> '.join(path)}。请根据此路径操作对应交换机上的流表。"
#                     print(f"[JSONBuilderAgent] ✅ 注入路径上下文: {extra_context}")
#             except Exception as e:
#                 print(f"[JSONBuilderAgent] ⚠️ 查询 shortest_path 接口失败: {e}")

#         # ✅ 关键：把你长规则 prompt 用上（不变）
#         json_prompt = self.load_json_builder_prompt()

#         # ✅ 改动点：逐步生成
#         json_array: List[dict] = []
#         total_calls = 0

#         for idx, step in enumerate(steps, 1):
#             step_prompt = self.build_step_prompt(step, extra_context=extra_context)

#             messages = [
#                 {"role": "system", "content": "你是网络拓扑与控制指令生成助手，必须只输出严格JSON（对象或数组），禁止输出<think>、解释文字、Markdown代码块。"},
#                 {"role": "user", "content": f"{json_prompt}\n\n{step_prompt}"}
#             ]

#             try:
#                 response = client.chat.completions.create(
#                     model="qwen-plus",
#                     # model="deepseek-chat",
#                     # model="phi4:14b",
#                     # model="phi3:medium",
#                     # model="qwen2.5-coder:32b",
#                     # model="codellama:70b",
#                     # model="mistral-small:24b",
#                     # model="llama3.1:latest",
#                     # model="deepseek-r1:32b",
#                     # model="deepseek-r1:70b",
#                     messages=messages,
#                     stream=False,
#                     temperature=0.0
#                 )

#                 total_calls += 1
#                 raw = response.choices[0].message.content.strip()
#                 print(f"\n[JSONBuilderAgent] 📥 Step {idx}/{len(steps)} 原始输出:\n{raw}")

#                 parsed = extract_pure_json(raw)
#                 print(f"[JSONBuilderAgent] 📥 Step {idx}/{len(steps)} 清洗后的输出:\n{parsed}")

#                 # 统一成 list[dict] 追加到总 json_array
#                 if isinstance(parsed, dict):
#                     parsed_list = [parsed]
#                 elif isinstance(parsed, list):
#                     parsed_list = parsed
#                 else:
#                     raise ValueError(f"Unexpected type from extract_pure_json: {type(parsed)}")

#                 for instr in parsed_list:
#                     if not isinstance(instr, dict):
#                         print(f"[JSONBuilderAgent] ⚠️ Step {idx} 指令不是 dict，跳过: {instr}")
#                         continue
#                     # ✅ action 兜底规范化
#                     if isinstance(instr.get("action"), str):
#                         instr["action"] = instr["action"].strip().lower()
#                     json_array.append(instr)

#                 print(f"[JSONBuilderAgent] ✅ Step {idx} token 使用量如下")
#                 record_tokens_from_response(response)

#             except Exception as e:
#                 print(f"[JSONBuilderAgent] ❌ Step {idx} LLM 调用或 JSON 解析失败: {e}")
#                 return

#         if not isinstance(json_array, list) or len(json_array) == 0:
#             print("[JSONBuilderAgent] ❌ 未生成任何 JSON 指令")
#             return

#         print(f"\n[JSONBuilderAgent] ✅ 逐步生成完成：LLM 调用次数={total_calls}，总指令数={len(json_array)}，trace_id={trace_id}")

#         # === 分发（保持你原逻辑不变） ===
#         for i, instr in enumerate(json_array):
#             instr["trace_id"] = trace_id
#             instr["intent_text"] = intent_text

#             if i == len(json_array) - 1:
#                 instr["final_step"] = True

#             print(f"[JSONBuilderAgent] 📤 发送指令: {instr.get('action')} trace_id={trace_id}")
#             send_intent(instr, sender="JSONBuilderAgent", trace_id=trace_id)

#     # ✅ 保留原函数不动（虽然逐步模式不再用它，但你说“其余逻辑不要变”，我就留着）
#     def build_batch_prompt(self, steps: List[str], extra_context: Optional[str] = None) -> str:
#         prompt_lines = []
#         if extra_context:
#             prompt_lines.append(f"[上下文信息]\n{extra_context}\n")

#         prompt_lines.append("[用户意图步骤]")
#         for step in steps:
#             prompt_lines.append(step)
#         prompt_lines.append("\n请根据以上步骤，生成对应的结构化 JSON 指令数组。")

#         return "\n".join(prompt_lines)