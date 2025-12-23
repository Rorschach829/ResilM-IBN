from backend.llm.prompt_templates import load_json_builder_prompt
from backend.llm.llm_utils import client
from backend.utils.utils import extract_json_from_response
from backend.utils.messagepool_utils import send_intent
from backend.coordinator.message_pool import message_pool
from backend.utils.token_utils import record_tokens_from_response
import uuid, json, requests
import re
from typing import List, Optional


class JSONBuilderAgent:
    def __init__(self):
        self.name = "JSONBuilderAgent"
        message_pool.subscribe("plan_steps", self.handle_plan)

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
                steps = [
                    s for s in steps
                    if not ("创建" in s and "拓扑" in s)
                ]
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

        # === 构建 Prompt ===
        prompt = self.build_batch_prompt(steps, extra_context=extra_context)

        system_prompt = load_json_builder_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            response = client.chat.completions.create(
                # model="deepseek-chat",
                # model="phi4:14b",
                # model="phi3:medium",
                # model="qwen2.5-coder:32b",
                # model="codellama:70b",
                # model="mistral-small:24b",
                # model="llama3.1:latest",
                model="deepseek-r1:32b",
                # model="deepseek-r1:70b",
                messages=messages,
                stream=False,
                temperature=0.0
            )
            content = response.choices[0].message.content.strip()
            print(f"[JSONBuilderAgent] 📥 LLM 原始输出:\n{content}")

            content = extract_json_from_response(content)
            json_array = json.loads(content)
        except Exception as e:
            print(f"[JSONBuilderAgent] ❌ LLM 调用或 JSON 解析失败: {e}")
            return

        if response:
            print("本次JSON_builder_agent调用llm的token使用量如下")
            record_tokens_from_response(response)
        else:
            raise Exception("LLM 响应为空，无法继续解析")

        if not isinstance(json_array, list):
            print("[JSONBuilderAgent] ❌ 返回结果不是 JSON 数组")
            return

        for i, instr in enumerate(json_array):
            instr["trace_id"] = trace_id
            instr["intent_text"] = intent_text

            if i == len(json_array) - 1:
                instr["final_step"] = True  # ✅ 给最后一条指令标记

            print(f"[JSONBuilderAgent] 📤 发送指令: {instr.get('action')} trace_id={trace_id}")
            send_intent(instr, sender="JSONBuilderAgent", trace_id=trace_id)





    def generate_json_instructions(self, plan_instr: dict) -> list:
        from backend.llm.prompt_templates import load_json_builder_prompt
        from backend.llm.llm_utils import client
        from backend.utils.utils import extract_json_from_response

        steps = plan_instr.get("steps", [])
        intent_text = plan_instr.get("intent_text", "")

        # 构建提示词
        prompt = self.build_batch_prompt(steps)
        system_prompt = load_json_builder_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False,
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        content = extract_json_from_response(content)
        return json.loads(content)


    def build_batch_prompt(self, steps: List[str], extra_context: Optional[str] = None) -> str:
        prompt_lines = []
        if extra_context:
            prompt_lines.append(f"[上下文信息]\n{extra_context}\n")

        prompt_lines.append("[用户意图步骤]")
        for i, step in enumerate(steps, 1):
            prompt_lines.append(f"{step}")
        prompt_lines.append("\n请根据以上步骤，生成对应的结构化 JSON 指令数组。")

        return "\n".join(prompt_lines)


