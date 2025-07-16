# backend/utils/logger.py

import os
import json
from datetime import datetime

BASE_LOG_DIR = "/data/gjw/Meta-IBN/logs"
CURRENT_LOG_FILE = None  # 🆕 当前正在记录的文件路径（每次创建拓扑会更新它）

# backend/utils/logger.py
def start_new_intent_log():
    global CURRENT_LOG_FILE
    now = datetime.now()
    ts = now.strftime("%Y%m%d_%H%M%S")
    file_name = f"topo_{ts}.jsonl"
    full_path = os.path.join(BASE_LOG_DIR, file_name)
    os.makedirs(BASE_LOG_DIR, exist_ok=True)
    CURRENT_LOG_FILE = full_path

    # ✅ 写入临时文件，供后续 link_up 用
    with open("/data/gjw/Meta-IBN/tmp/intent_log_path.txt", "w") as f:
        f.write(CURRENT_LOG_FILE)

    return CURRENT_LOG_FILE

def get_latest_log_file():
    global CURRENT_LOG_FILE
    if CURRENT_LOG_FILE:
        return CURRENT_LOG_FILE
    try:
        with open("/tmp/intent_log_path.txt", "r") as f:
            CURRENT_LOG_FILE = f.read().strip()
            return CURRENT_LOG_FILE
    except Exception:
        return None


def log_intent(intent_text: str, instruction: dict, result: str):
    global CURRENT_LOG_FILE
    if not CURRENT_LOG_FILE:
        # fallback（首次使用未初始化）
        start_new_intent_log()

    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "intent": intent_text,
        "instruction": instruction,
        "result": result
    }

    with open(CURRENT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n\n")
