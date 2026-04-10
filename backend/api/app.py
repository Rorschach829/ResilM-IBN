from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from backend.agents.intent_agent import IntentAgent
from backend.net_simulation.mininet_manager import run_mininet_code, get_current_topology, stop_topology,rebuild_topology
import backend.net_simulation.mininet_manager as mm
from backend.utils.token_utils import get_total_tokens
from backend.utils.logger import log_intent, start_new_intent_log,init_logger
app = Flask(__name__,
            template_folder="../../frontend/templates",
            static_folder="../../frontend/static")
CORS(app, resources={r"/*": {"origins": "*"}})
from backend.utils.messagepool_utils import send_intent
from backend.agents.json_builder_agent import JSONBuilderAgent
import uuid
from backend.coordinator.message_pool import message_pool
from backend.utils.logger import CURRENT_LOG_FILE
# from test.temporary import find_entries_by_trace_id
import threading
import time
from datetime import datetime
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
        # ✅ 打印当前时间戳（可读格式和Unix秒）
        now = datetime.now()
        print(f"[INTENT RECEIVED] 时间: {now.strftime('%Y-%m-%d %H:%M:%S')}  (Unix: {int(now.timestamp())})")

        instructions = intent_agent.intent_to_instruction(intent_text)

        # if any(instr.get("action") == "create_topology" for instr in instructions):
        # 每当发送意图的时候都创建一个拓扑
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


# 判断服务端是否空闲
@app.route("/is_idle", methods=["GET"])
def is_idle():
    return jsonify({"idle": not is_executing})


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

# ---- token counter in Flask process ----
from backend.utils import token_counter

@app.post("/token/reset")
def token_reset():
    token_counter.reset()
    return {"ok": True}

@app.get("/token/summary")
def token_summary():
    return token_counter.summary()

# 清理拓扑并且清空Current_log_file
@app.route("/cleanup", methods=["POST"])
def cleanup_topology():
    try:
        stop_topology()
        return jsonify({"success": True, "message": "✅ 已清空拓扑"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/shortest_path")
def shortest_path():
    src = request.args.get("src")
    dst = request.args.get("dst")

    try:
        path = get_path_switches(src, dst)  # 或其他内部方法
        return jsonify({"path": path, "success": True})
    except Exception as e:
        return jsonify({"path": [], "success": False, "error": str(e)}), 400

if __name__ == "__main__":
    init_logger()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

