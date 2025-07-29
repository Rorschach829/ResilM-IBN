from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from backend.agents.intent_agent import IntentAgent
from backend.net_simulation.mininet_manager import run_mininet_code, get_current_topology, stop_topology,rebuild_topology
from backend.net_simulation.instruction_executor import execute_instruction
import backend.net_simulation.mininet_manager as mm
from backend.utils.token_utils import get_total_tokens
from backend.utils.logger import log_intent, start_new_intent_log
app = Flask(__name__, 
            template_folder="/data/gjw/Meta-IBN/frontend/templates", 
            static_folder="/data/gjw/Meta-IBN/frontend/static")
CORS(app, resources={r"/*": {"origins": "*"}})
from backend.utils.messagepool_utils import send_intent
from backend.agents.json_builder_agent import JSONBuilderAgent
intent_agent = IntentAgent()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/intent", methods=["POST"])
def handle_intent():
    data = request.json
    intent_text = data.get("intent", "")
    if not intent_text:
        return jsonify({"error": "意图内容不能为空"}), 400
    
    try:
        instructions = intent_agent.intent_to_instruction(intent_text)
        all_outputs = []

        for instr in instructions:
            action = instr.get("action", "")

            if action == "plan_steps":
                from backend.agents.json_builder_agent import JSONBuilderAgent
                jb = JSONBuilderAgent()
                json_instrs = jb.generate_json_instructions(instr)
                steps = instr.get("steps", [])

                for i, sub_instr in enumerate(json_instrs):
                    result = execute_instruction(sub_instr)
                    all_outputs.append({
                        "step": steps[i] if i < len(steps) else None,
                        "action": sub_instr.get("action"),
                        "result": result
                    })
            else:
                instr["intent_text"] = intent_text

                result = execute_instruction(instr)
                all_outputs.append({
                    "step": None,
                    "action": instr.get("action"),
                    "result": result
                })

    except Exception as e:
        return jsonify({"error": f"指令执行失败: {str(e)}"}), 500

    return jsonify({
        "message": "✅ 所有指令执行完成",
        "output": all_outputs,
        "success": True
    })




# 获取当前拓扑
@app.route("/topology", methods=["GET"])
def topology():
    topo_json = get_current_topology()
    print("[DEBUG] 当前 global_net:", mm.global_net)
    print("[DEBUG] 当前 topology 返回内容:", topo_json)
    return jsonify(topo_json)

# 删除拓扑
@app.route("/stop", methods=["POST"])
def stop():
    message = stop_topology()
    return jsonify({"message": message})

# 获取当前token消耗
@app.route("/token_stats", methods=["GET"])
def token_stats():
    return jsonify({"total_tokens": get_total_tokens()})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

