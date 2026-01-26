import sys
import os
import time
import json
import requests
import csv
from datetime import datetime

import subprocess
import signal
#必须单独启动start_all
START_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def start_system():
    return subprocess.Popen(
        ["python", "start_all.py"],
        cwd=START_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def stop_system(proc):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ============ 配置 ============

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTENT_FILE = os.path.join(BASE_DIR, "intent_bu.txt")
LOG_PATH_FILE = os.path.join(BASE_DIR, "../tmp/intent_log_path.txt")
RESULT_BASE_DIR = os.path.join(BASE_DIR, "result")

API_INTENT_URL = "http://localhost:5000/intent"
API_CLEANUP_URL = "http://localhost:5000/cleanup"
API_TOKEN_RESET = "http://localhost:5000/token/reset"
API_TOKEN_SUMMARY = "http://localhost:5000/token/summary"

POLL_INTERVAL = 1
NUM_ROUNDS = 10

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

def wait_for_final_step(trace_id, log_path, timeout_sec=600):
    print(f"[WAIT] 等待 trace_id={trace_id} 执行完成...")

    start = time.time()
    while True:
        entries = load_all_log_entries(log_path)
        matched = [e for e in entries if str(e.get("trace_id", "")).strip() == trace_id.strip()]

        # 别用 `is True`，很多时候 final_step 可能是 1 / "true"
        if any(bool(e.get("final_step")) for e in matched):
            return matched

        if time.time() - start > timeout_sec:
            print("[WAIT] 超时：未检测到 final_step，返回当前已匹配日志。")
            return matched

        time.sleep(POLL_INTERVAL)

def is_success(entries):
    # 你原来是 all(result is True)，如果有 entry 没 result 会直接失败
    # 如果你希望“只要没有明确 False 就算流程成功”，用下面这一行：
    return all(e.get("result") is not False for e in entries)

def cleanup_topology():
    print("[CLEANUP] 清空拓扑中...")
    try:
        response = requests.post(API_CLEANUP_URL, timeout=30)
        if response.status_code == 200:
            print("[CLEANUP] 拓扑清理完成。")
            time.sleep(5)
            print("[CLEANUP] 5秒等待已完成。")


        else:
            print(f"[CLEANUP] 清理失败: {response.status_code}")
    except Exception as e:
        print(f"[CLEANUP] 请求异常: {e}")

def token_reset():
    try:
        r = requests.post(API_TOKEN_RESET, timeout=5)
        if r.status_code != 200:
            print(f"[TOKEN] reset failed: {r.status_code} {r.text}")
    except Exception as e:
        print(f"[TOKEN] reset exception: {e}")

def token_summary():
    try:
        r = requests.get(API_TOKEN_SUMMARY, timeout=5)
        if r.status_code != 200:
            print(f"[TOKEN] summary failed: {r.status_code} {r.text}")
            return 0, 0
        data = r.json()
        return int(data.get("intent_token", 0)), int(data.get("json_token", 0))
    except Exception as e:
        print(f"[TOKEN] summary exception: {e}")
        return 0, 0

# ============ 主逻辑 ============

def main():
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
    result_dir = os.path.join(RESULT_BASE_DIR, f"intent_test_{timestamp_str}")
    os.makedirs(result_dir, exist_ok=True)

    result_file = os.path.join(result_dir, f"intent_summary_{timestamp_str}.csv")

    with open(INTENT_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    with open(result_file, "w", newline="", encoding="utf-8", buffering=1) as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["intent_id", "rounds", "steps", "avg_time", "is_successful", "intent_token", "json_token"])
        csvfile.flush()
        os.fsync(csvfile.fileno())

        for idx, intent in enumerate(lines, 1):
            print(f"========== 测试意图 {idx}: {intent} ==========")

            for round_num in range(1, NUM_ROUNDS + 1):
                print(f"----- 第 {round_num} 轮开始 -----")
                start_time = int(time.time())

                try:
                    # ✅ 每轮开始前：让后端清空 token 计数（在同一后端进程里）
                    
                    token_reset()


                    response = requests.post(API_INTENT_URL, json={"intent": intent}, timeout=300)
                    if response.status_code != 200:
                        print(f"❌ 接口调用失败: {response.status_code}")
                        writer.writerow([idx, round_num, "N/A", "N/A", "接口错误", 0, 0])
                        csvfile.flush(); os.fsync(csvfile.fileno())
                        cleanup_topology()
                        continue

                    resp_json = response.json()
                    trace_id = resp_json.get("trace_id")
                    if not trace_id:
                        print("❌ 无 trace_id 返回")
                        writer.writerow([idx, round_num, "N/A", "N/A", "无trace_id", 0, 0])
                        csvfile.flush(); os.fsync(csvfile.fileno())
                        cleanup_topology()
                        continue

                    log_path = read_latest_log_path()
                    entries = wait_for_final_step(trace_id, log_path)

                    end_time = next((e.get("instruction", {}).get("timestamp") for e in entries if e.get("final_step")), None)
                    duration = end_time - start_time if end_time else "?"
                    steps = len(entries)
                    success = is_success(entries)

                    # ✅ 执行结束后：从后端拿 token 汇总
                    intent_tokens, json_tokens = token_summary()

                    writer.writerow([
                        idx,
                        round_num,
                        steps,
                        duration,
                        "Y" if success else "N",
                        intent_tokens,
                        json_tokens
                    ])
                    csvfile.flush()
                    os.fsync(csvfile.fileno())

                    print(f"✅ 完成: 步骤数={steps}, 耗时={duration}s, 成功={success}, intent_token={intent_tokens}, json_token={json_tokens}")
                    
                except Exception as e:
                    print(f"❌ 异常: {e}")
                    writer.writerow([idx, round_num, "异常", "异常", "N", 0, 0])
                    csvfile.flush()
                    os.fsync(csvfile.fileno())

                cleanup_topology()

if __name__ == "__main__":
    main()