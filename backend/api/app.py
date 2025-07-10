from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from backend.agents.intent_agent import IntentAgent
from backend.net_simulation.mininet_manager import run_mininet_code, get_current_topology, stop_topology,rebuild_topology
from backend.net_simulation.instruction_executor import execute_instruction

app = Flask(__name__, template_folder="/data/gjw/Meta-IBN/backend/templates")
CORS(app, resources={r"/*": {"origins": "*"}})

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
        instruction = intent_agent.intent_to_instruction(intent_text)
        print("解析后的指令:", instruction)
    except Exception as e:
        return jsonify({"error": f"意图解析失败: {str(e)}"}), 500

    try:
        output = execute_instruction(instruction)
    except Exception as e:
        return jsonify({"error": f"指令执行失败: {str(e)}"}), 500

    return jsonify({
        "message": "✅ 指令执行成功",
        "instruction": instruction,
        "output": output
    })

@app.route("/topology", methods=["GET"])
def topology():
    topo_json = get_current_topology()
    return jsonify(topo_json)

@app.route("/stop", methods=["POST"])
def stop():
    message = stop_topology()
    return jsonify({"message": message})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
