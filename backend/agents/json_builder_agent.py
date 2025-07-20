from backend.llm.prompt_templates import load_json_builder_prompt
from backend.llm.llm_utils import client
from backend.utils.utils import extract_json_from_response
from backend.utils.messagepool_utils import send_intent
from backend.coordinator.message_pool import message_pool
import uuid, json, requests

class JSONBuilderAgent:
    def __init__(self):
        self.name = "JSONBuilderAgent"
        message_pool.subscribe("plan_steps", self.handle_plan)

    def handle_plan(self, message: dict):

        steps = message.get("steps", [])
        intent_text = message.get("intent_text", "")
        trace_id = message.get("trace_id", str(uuid.uuid4()))

        print(f"[JSONBuilderAgent] ✅ 批处理 {len(steps)} 条步骤")

        # === 🧠 简洁判断：只要当前拓扑非空，就跳过创建步骤 ===
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

        # === 构建提示词 ===
        prompt = self.build_batch_prompt(steps)

        messages = [
            {"role": "system", "content": "你是网络 JSON 指令生成专家，只输出合法 JSON 数组"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=False
            )
            content = response.choices[0].message.content.strip()
            print(f"[JSONBuilderAgent] 📥 LLM 原始输出:\n{content}")

            content = extract_json_from_response(content)
            json_array = json.loads(content)
        except Exception as e:
            print(f"[JSONBuilderAgent] ❌ LLM 调用或 JSON 解析失败: {e}")
            return

        if not isinstance(json_array, list):
            print("[JSONBuilderAgent] ❌ 返回结果不是 JSON 数组")
            return

        for instr in json_array:
            send_intent(instr, sender="JSONBuilderAgent", trace_id=trace_id)

    # def handle_plan(self, message: dict):
    #     steps = message.get("steps", [])
    #     intent_text = message.get("intent_text", "")
    #     trace_id = message.get("trace_id", str(uuid.uuid4()))

    #     print(f"[JSONBuilderAgent] ✅ 批处理 {len(steps)} 条步骤")
    #     prompt = self.build_batch_prompt(steps)

    #     messages = [
    #         {"role": "system", "content": "你是网络 JSON 指令生成专家，只输出合法 JSON 数组"},
    #         {"role": "user", "content": prompt}
    #     ]

    #     try:
    #         response = client.chat.completions.create(
    #             model="deepseek-chat",
    #             messages=messages,
    #             stream=False
    #         )
    #         content = response.choices[0].message.content.strip()
    #         print(f"[JSONBuilderAgent] 📥 LLM 原始输出:\n{content}")

    #         # 
    #         content = extract_json_from_response(content)
    #         json_array = json.loads(content)
    #     except Exception as e:
    #         print(f"[JSONBuilderAgent] ❌ LLM 调用或解析失败: {e}")
    #         return

    #     if not isinstance(json_array, list):
    #         print("[JSONBuilderAgent] ❌ 返回结果不是 JSON 数组")
    #         return

    #     for instr in json_array:
    #         send_intent(instr, sender="JSONBuilderAgent", trace_id=trace_id)


    def build_batch_prompt(self, steps: list[str]) -> str:
        base_prompt = load_json_builder_prompt()
        steps_block = "\n".join([step.strip() for step in steps])
        return f"{base_prompt}\n\n以下是操作步骤：\n{steps_block}"
