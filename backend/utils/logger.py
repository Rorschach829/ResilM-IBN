import os
import json
from datetime import datetime
import glob

BASE_LOG_DIR = "/data/gjw/Meta-IBN/logs"
CURRENT_LOG_FILE = None  # 当前日志文件
TMP_DIR = "/data/gjw/Meta-IBN/tmp"
TMP_LOG_PATH_FILE = os.path.join(TMP_DIR, "intent_log_path.txt")


def init_logger():
    global CURRENT_LOG_FILE
    CURRENT_LOG_FILE = None

def start_new_intent_log():
    global CURRENT_LOG_FILE
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    file_name = f"topo_{ts}.jsonl"
    full_path = os.path.join(BASE_LOG_DIR, file_name)
    os.makedirs(BASE_LOG_DIR, exist_ok=True)
    CURRENT_LOG_FILE = full_path

    os.makedirs(TMP_DIR, exist_ok=True)
    with open(TMP_LOG_PATH_FILE, "w") as f:
        f.write(CURRENT_LOG_FILE)

    # clean_old_logs(max_keep=2)
    return CURRENT_LOG_FILE



def get_latest_log_file():
    global CURRENT_LOG_FILE
    if CURRENT_LOG_FILE:
        return CURRENT_LOG_FILE
    try:
        with open(TMP_LOG_PATH_FILE, "r") as f:
            CURRENT_LOG_FILE = f.read().strip()
            return CURRENT_LOG_FILE
    except Exception:
        return None


# ✅ 原始log_intent，保留兼容性，但写入结构化字段
def log_intent(intent_text: str, instruction: dict, result: str):
    global CURRENT_LOG_FILE
    if not CURRENT_LOG_FILE:
        start_new_intent_log()

    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "intent": intent_text,
        "instruction": instruction,
        "result": result  # 兼容原格式：可以是字符串，也可以是布尔值
    }

    with open(CURRENT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n\n")
        f.flush()


# ✅ 更推荐的结构化日志记录方式
def record_agent_result(message: dict, result: bool, agent_name: str, extra_info: str = "", value=None, threshold=None):
    intent_text = message.get("intent_text", "(未提供原始意图)")
    trace_id = message.get("trace_id", "")
    action = message.get("action", "unknown_action")

    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trace_id": trace_id,
        "sender": agent_name,
        "action": action,
        "intent": intent_text,
        "instruction": message,
        "result": result,
        "message": extra_info or ("✅ 执行成功" if result else "❌ 执行失败")
    }

    if message.get("final_step"):
        record["final_step"] = True

    if value:
        record["value"] = value
    if threshold:
        record["threshold"] = threshold

    global CURRENT_LOG_FILE
    if not CURRENT_LOG_FILE:
        start_new_intent_log()

    with open(CURRENT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n\n")
        f.flush()


def clean_old_logs(max_keep: int = 20):
    log_files = sorted(
        glob.glob(os.path.join(BASE_LOG_DIR, "topo_*.jsonl")),
        key=os.path.getmtime,
        reverse=True
    )
    to_delete = log_files[max_keep:]
    for f in to_delete:
        try:
            os.remove(f)
            print(f"[LOG CLEAN] 已删除旧日志文件: {f}")
        except Exception as e:
            print(f"[LOG CLEAN] 删除失败: {f}, 错误: {e}")
