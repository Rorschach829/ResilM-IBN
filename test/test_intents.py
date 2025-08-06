
import os
import time
import json
import requests
import csv
from datetime import datetime

# ============ 配置 ============

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTENT_FILE = os.path.join(BASE_DIR, "intent.txt")
LOG_PATH_FILE = os.path.join(BASE_DIR, "../tmp/intent_log_path.txt")
RESULT_BASE_DIR = os.path.join(BASE_DIR, "../result")
API_INTENT_URL = "http://localhost:5000/intent"
API_CLEANUP_URL = "http://localhost:5000/cleanup"
POLL_INTERVAL = 1
NUM_ROUNDS = 5

# ============ 工具函数 ============

def read_latest_log_path():
    with open(LOG_PATH_FILE, "r") as f:
        return f.read().strip()

def load_all_log_entries(log_path):
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    blocks = content.strip().split("\n\n")
    entries = []
    for block in blocks:
        try:
            entry = json.loads(block)
            entries.append(entry)
        except Exception as e:
            print(f"[LOG] JSON decode failed: {e}")
    return entries

def wait_for_final_step(trace_id, log_path):
    print(f"[WAIT] 等待 trace_id={trace_id} 执行完成...")

    while True:
        entries = load_all_log_entries(log_path)
        matched = [e for e in entries if str(e.get("trace_id", "")).strip() == trace_id.strip()]
        if any(e.get("final_step") is True for e in matched):
            return matched
        time.sleep(POLL_INTERVAL)

def is_success(entries):
    return all(e.get("result") is True for e in entries)

def cleanup_topology():
    print("[CLEANUP] 清空拓扑中...")
    try:
        response = requests.post(API_CLEANUP_URL)
        if response.status_code == 200:
            print("[CLEANUP] 拓扑清理完成。")
        else:
            print(f"[CLEANUP] 清理失败: {response.status_code}")
    except Exception as e:
        print(f"[CLEANUP] 请求异常: {e}")

# ============ 主逻辑 ============

def main():
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
    result_dir = os.path.join(RESULT_BASE_DIR, f"intent_test_{timestamp_str}")
    os.makedirs(result_dir, exist_ok=True)

    result_file = os.path.join(result_dir, f"intent_summary_{timestamp_str}.csv")

    with open(INTENT_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    with open(result_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["编号", "轮次", "步骤数", "耗时(秒)", "成功"])

        for idx, intent in enumerate(lines, 1):
            print(f"========== 测试意图 {idx}: {intent} ==========")

            for round_num in range(1, NUM_ROUNDS + 1):
                print(f"----- 第 {round_num} 轮开始 -----")
                start_time = int(time.time())

                try:
                    response = requests.post(API_INTENT_URL, json={"intent": intent})
                    if response.status_code != 200:
                        print(f"❌ 接口调用失败: {response.status_code}")
                        writer.writerow([idx, round_num, "N/A", "N/A", "接口错误"])
                        continue

                    resp_json = response.json()
                    trace_id = resp_json.get("trace_id")
                    if not trace_id:
                        print("❌ 无 trace_id 返回")
                        writer.writerow([idx, round_num, "N/A", "N/A", "无trace_id"])
                        continue

                    log_path = read_latest_log_path()
                    entries = wait_for_final_step(trace_id, log_path)
                    end_time = next((e.get("instruction", {}).get("timestamp") for e in entries if e.get("final_step")), None)
                    duration = end_time - start_time if end_time else "?"
                    steps = len(entries)
                    success = is_success(entries)

                    writer.writerow([idx, round_num, steps, duration, "是" if success else "否"])
                    print(f"✅ 完成: 步骤数={steps}, 耗时={duration}s, 成功={success}")

                except Exception as e:
                    print(f"❌ 异常: {e}")
                    writer.writerow([idx, round_num, "异常", "异常", "否"])

                cleanup_topology()

if __name__ == "__main__":
    main()
