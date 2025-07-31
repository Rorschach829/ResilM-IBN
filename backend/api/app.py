from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from backend.agents.intent_agent import IntentAgent
from backend.net_simulation.mininet_manager import run_mininet_code, get_current_topology, stop_topology,rebuild_topology
from backend.net_simulation.instruction_executor import execute_instruction
import backend.net_simulation.mininet_manager as mm
from backend.utils.token_utils import get_total_tokens
from backend.utils.logger import log_intent, start_new_intent_log,init_logger
app = Flask(__name__, 
            template_folder="/data/gjw/Meta-IBN/frontend/templates", 
            static_folder="/data/gjw/Meta-IBN/frontend/static")
CORS(app, resources={r"/*": {"origins": "*"}})
from backend.utils.messagepool_utils import send_intent
from backend.agents.json_builder_agent import JSONBuilderAgent
import uuid
from backend.coordinator.message_pool import message_pool

init_logger()

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
        if any(instr.get("action") == "create_topology" for instr in instructions):
            start_new_intent_log()
        trace_id = str(uuid.uuid4())

        for instr in instructions:
            instr["intent_text"] = intent_text
            instr["trace_id"] = trace_id
            message_pool.publish(instr, sender="IntentAgent")

        return jsonify({
            "message": "✅ 指令已成功发布至多智能体系统",
            "trace_id": trace_id,
            "instruction_count": len(instructions),
            "success": True
        })

    except Exception as e:
        return jsonify({"error": f"指令处理失败: {str(e)}"}), 500

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
    init_logger()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

