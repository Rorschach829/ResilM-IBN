import os
import json
from datetime import datetime

BASE_LOG_DIR = "/data/gjw/Meta-IBN/logs"

def log_intent(intent_text: str, instruction: dict, result: str):
    now = datetime.now()
    day_folder = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    # 拼接路径
    log_dir = os.path.join(BASE_LOG_DIR, day_folder)
    log_path = os.path.join(log_dir, "intent_log.jsonl")

    # 确保目录存在
    os.makedirs(log_dir, exist_ok=True)

    # 构造日志项
    log_entry = {
        "timestamp": timestamp,
        "intent": intent_text,
        "instruction": instruction,
        "result": result
    }

    with open(log_path, "a", encoding="utf-8") as f:
        # 横向很长显示
        # f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        f.write(json.dumps(log_entry, ensure_ascii=False, indent=2) + "\n\n")

