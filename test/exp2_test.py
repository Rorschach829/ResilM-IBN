# 用于测试实验2自愈功能
import os
import re
import json
import time
import csv
import requests
from datetime import datetime

# =================== 配置路径 ===================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

EXP2_INTENT_FILE = os.path.join(BASE_DIR, "result2/exp2.txt")
LOG_PATH_FILE = os.path.join(BASE_DIR, "../tmp/intent_log_path.txt")
API_URL = "http://localhost:5000/intent"

# ========== 【默认方式：每次新建实验目录和文件，用于新建一次实验】 ==========
# timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# EXP2_OUTPUT_DIR = os.path.join(BASE_DIR, f"result2/exp2_test_{timestamp}")
# os.makedirs(EXP2_OUTPUT_DIR, exist_ok=True)
# EXP2_CSV_FILE = os.path.join(EXP2_OUTPUT_DIR, f"exp2_{timestamp}.csv")


# ========== 【改为写入固定的实验结果文件,用于多轮实验数据添加】 ==========
EXP2_FIXED_TIMESTAMP = "20250808_150011"
EXP2_OUTPUT_DIR = os.path.join(BASE_DIR, f"result2/exp2_test_{EXP2_FIXED_TIMESTAMP}")
EXP2_CSV_FILE = os.path.join(EXP2_OUTPUT_DIR, f"exp2_{EXP2_FIXED_TIMESTAMP}.csv")


# ✅ 自动生成带时间戳的结果路径和文件名
# timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# EXP2_OUTPUT_DIR = os.path.join(BASE_DIR, f"result2/exp2_test_{timestamp}")
# os.makedirs(EXP2_OUTPUT_DIR, exist_ok=True)
# EXP2_CSV_FILE = os.path.join(EXP2_OUTPUT_DIR, f"exp2_{timestamp}.csv")


# =================== 工具函数 ===================

def read_intents(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def read_latest_log_path():
    with open(LOG_PATH_FILE, "r") as f:
        return f.read().strip()

def extract_host_pair(text):
    match = re.findall(r"h\d+", text)
    if len(match) >= 2:
        return f"{match[0]}-{match[1]}"
    return "unknown"

def load_log_entries(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    blocks = content.strip().split("\n\n")
    entries = []
    for block in blocks:
        try:
            entry = json.loads(block)
            entries.append(entry)
        except Exception as e:
            print(f"[解析失败] 跳过一条日志块: {e}")
    return entries

def wait_for_final(trace_id, log_path, timeout=60):
    print(f"[WAIT] 等待 trace_id={trace_id} 执行完成...")
    start = time.time()
    while time.time() - start < timeout:
        entries = load_log_entries(log_path)
        matched = [e for e in entries if str(e.get("trace_id", "")).strip() == trace_id.strip()]
        if any(e.get("final_step") is True for e in matched):
            return matched
        time.sleep(1)
    raise TimeoutError("等待日志超时")

def analyze_entries(intent_id, round_id, intent, entries, start_time):
    host_pair = extract_host_pair(intent)
    repair_triggered = any(e.get("action") == "repair_suggestion" for e in entries)
    is_ping_success_before = not any("无法" in str(e.get("message", "")) for e in entries)
    repair_success = any(
        e.get("final_step") is True and 
        "可以" in str(e.get("message", "")) and 
        any(ee.get("action") == "repair_suggestion" for ee in entries)
        for e in entries
    )
    final_result = any(
        e.get("final_step") is True and "可以" in str(e.get("message", "")) 
        for e in entries
    )
    end_entry = next((e for e in entries if e.get("final_step") is True), None)
    if end_entry:
        end_time = end_entry.get("instruction", {}).get("timestamp", 0)
        total_time = end_time - start_time
    else:
        total_time = -1

    return {
        "intent_id": intent_id,
        "round_id": round_id,
        "host_pair": host_pair,
        "repair_triggered": repair_triggered,
        "is_ping_success_before": is_ping_success_before,
        "repair_success": repair_success,
        "final_result": final_result,
        "total_time": total_time
    }

def get_latest_round(csv_path):
    if not os.path.exists(csv_path):
        return 0
    rounds = set()
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rounds.add(int(row["round_id"]))
    return max(rounds) if rounds else 0

# =================== 主测试函数 ===================

def main():
    print(f"[INFO] 当前实验结果将保存至: {EXP2_CSV_FILE}")

    intents = read_intents(EXP2_INTENT_FILE)
    round_id = get_latest_round(EXP2_CSV_FILE) + 1
    print(f"[INFO] 当前为第 {round_id} 轮测试，共 {len(intents)} 条意图")

    with open(EXP2_CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "intent_id", "round_id", "host_pair", "repair_triggered", 
            "is_ping_success_before", "repair_success", 
            "final_result", "total_time"
        ])
        if f.tell() == 0:
            writer.writeheader()

        for offset, intent in enumerate(intents):
            intent_id = offset + 1  # 固定为意图文件行号
            print(f"\n🚀 执行 intent_id={intent_id}: {intent}")
            start_time = int(time.time())

            try:
                resp = requests.post(API_URL, json={"intent": intent})
                if resp.status_code != 200:
                    print(f"[ERROR] 请求失败: {resp.status_code}")
                    continue
                trace_id = resp.json().get("trace_id")
                if not trace_id:
                    print("[ERROR] 无 trace_id 返回")
                    continue

                log_path = read_latest_log_path()
                entries = wait_for_final(trace_id, log_path)
                stats = analyze_entries(intent_id, round_id, intent, entries, start_time)
                writer.writerow(stats)
                print(f"✅ 完成: {stats}")

            except Exception as e:
                print(f"[EXCEPTION] 执行异常: {e}")

        # =================== 所有意图测试完成，重新按 intent_id 排序 ===================
    try:
        print("\n[POST-PROCESS] 正在重新排序 exp2.csv ...")
        with open(EXP2_CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        # 按 intent_id 和 round_id 排序
        rows.sort(key=lambda r: (int(r["intent_id"]), int(r["round_id"])))

        with open(EXP2_CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print("[POST-PROCESS] ✅ 排序完成，exp2.csv 已更新")
    except Exception as e:
        print(f"[ERROR] 排序失败: {e}")


if __name__ == "__main__":
    main()
