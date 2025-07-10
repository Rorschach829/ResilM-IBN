from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from backend.agents.intent_agent import IntentAgent
from backend.net_simulation.mininet_manager import run_mininet_code, get_current_topology, stop_topology,rebuild_topology


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
        return jsonify({"error": "Intent text required"}), 400

    try:
        code = rebuild_topology(intent_text)
    except Exception as e:
        return jsonify({"error": f"LLM调用失败: {str(e)}"}), 500

    try:
        output = run_mininet_code(code)
    except Exception as e:
        return jsonify({"error": f"Mininet运行失败: {str(e)}"}), 500

    return jsonify({"message": "拓扑创建成功", "code": code, "output": output})

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
