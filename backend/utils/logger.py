# # backend/utils/logger.py

# import os
# import json
# from datetime import datetime
# import glob

# BASE_LOG_DIR = "/data/gjw/Meta-IBN/logs"
# CURRENT_LOG_FILE = None  # 🆕 当前正在记录的文件路径（每次创建拓扑会更新它）

# # 初始化
# def init_logger():
#     global CURRENT_LOG_FILE
#     CURRENT_LOG_FILE = None

# # backend/utils/logger.py
# def start_new_intent_log():
#     global CURRENT_LOG_FILE
#     now = datetime.now()
#     ts = now.strftime("%Y%m%d_%H%M%S")
#     file_name = f"topo_{ts}.jsonl"
#     full_path = os.path.join(BASE_LOG_DIR, file_name)
#     os.makedirs(BASE_LOG_DIR, exist_ok=True)
#     CURRENT_LOG_FILE = full_path

#    # ✅ 补充创建 tmp 目录
#     tmp_dir = "/data/gjw/Meta-IBN/tmp"
#     os.makedirs(tmp_dir, exist_ok=True)

#     # ✅ 写入临时文件，供后续 link_up 用
#     with open(os.path.join(tmp_dir, "intent_log_path.txt"), "w") as f:
#         f.write(CURRENT_LOG_FILE)

#     clean_old_logs(max_keep=2)
#     return CURRENT_LOG_FILE

# def get_latest_log_file():
#     global CURRENT_LOG_FILE
#     if CURRENT_LOG_FILE:
#         return CURRENT_LOG_FILE
#     try:
#         with open("/tmp/intent_log_path.txt", "r") as f:
#             CURRENT_LOG_FILE = f.read().strip()
#             return CURRENT_LOG_FILE
#     except Exception:
#         return None


# def log_intent(intent_text: str, instruction: dict, result: str):
#     global CURRENT_LOG_FILE
#     if not CURRENT_LOG_FILE:
#         # fallback（首次使用未初始化）
#         start_new_intent_log()

#     log_entry = {
#         "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#         "intent": intent_text,
#         "instruction": instruction,
#         "result": result
#     }

#     with open(CURRENT_LOG_FILE, "a", encoding="utf-8") as f:
#         f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n\n")

# # 清理旧的日志文件，只保留最近3个
# def clean_old_logs(max_keep: int = 2):
#     log_files = sorted(
#         glob.glob(os.path.join(BASE_LOG_DIR, "topo_*.jsonl")),
#         key=os.path.getmtime,
#         reverse=True
#     )

#     to_delete = log_files[max_keep:]  # 超出保留数量的文件
#     for f in to_delete:
#         try:
#             os.remove(f)
#             print(f"[LOG CLEAN] 已删除旧日志文件: {f}")
#         except Exception as e:
#             print(f"[LOG CLEAN] 删除失败: {f}, 错误: {e}")

# # 将结果记录到json文件当中
# def record_agent_result(message: dict, result: str, agent_name: str, extra_info: str = ""):
#     intent_text = message.get("intent_text", "(未提供原始意图)")
#     record = {
#         "trace_id": message.get("trace_id"),
#         "sender": agent_name,
#         "action": message.get("action"),
#         "result": result
#     }
#     if extra_info:
#         record["info"] = extra_info

#     log_intent(intent_text, message, result)
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

    clean_old_logs(max_keep=2)
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

    if value:
        record["value"] = value
    if threshold:
        record["threshold"] = threshold

    global CURRENT_LOG_FILE
    if not CURRENT_LOG_FILE:
        start_new_intent_log()

    with open(CURRENT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n\n")


def clean_old_logs(max_keep: int = 2):
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
