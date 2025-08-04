import os
import json
import csv
import time
import requests
from datetime import datetime
from pathlib import Path

# === 配置路径 ===
intent_file = "/data/gjw/Meta-IBN/test/intent.txt"
log_dir = "/data/gjw/Meta-IBN/logs"
output_path = "/data/gjw/Meta-IBN/result/intent_test_result_20250804_013125.csv"

# === 加载意图列表（只取最后两条）===
with open(intent_file, "r", encoding="utf-8") as f:
    intent_list = [line.strip() for line in f if line.strip()]
intent_subset = intent_list[-2:]
start_intent_idx = len(intent_list) - 2

# === 准备追加写入 CSV 文件 ===
csvfile = open(output_path, "a", newline="", encoding="utf-8")
writer = csv.DictWriter(csvfile, fieldnames=["意图编号", "执行轮次", "步骤数", "耗时(s)", "是否成功"])

def find_entries_by_trace_id(log_dir, trace_id):
    files = sorted(Path(log_dir).glob("topo_*.jsonl"), key=os.path.getmtime)
    if not files:
        return []
    latest_file = files[-1]
    with open(latest_file, "r", encoding="utf-8") as f:
        blocks = f.read().strip().split("\n\n")
        entries = []
        for block in blocks:
            try:
                record = json.loads(block)
                if record.get("trace_id") == trace_id:
                    entries.append(record)
            except Exception:
                continue
    return entries

def wait_for_final_step(log_dir, trace_id, timeout=60, interval=0.5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        entries = find_entries_by_trace_id(log_dir, trace_id)
        if any(e.get("final_step") is True for e in entries):
            return entries
        time.sleep(interval)
    print(f"  ⏳ 等待超时：trace_id={trace_id} 无 final_step")
    return find_entries_by_trace_id(log_dir, trace_id)

# === 补测循环 ===
for i, intent in enumerate(intent_subset):
    intent_id = start_intent_idx + i + 1
    print(f"\n🚀 补测意图 {intent_id}: {intent}")

    for run_idx in range(5):
        print(f"  ⏱️ 第 {run_idx + 1}/5 次执行")

        try:
            start_time = datetime.now()
            resp = requests.post(
                "http://localhost:5000/intent",
                json={"intent": intent},
                timeout=60
            )
            if resp.status_code != 200:
                raise Exception(f"返回码异常: {resp.status_code}")
            data = resp.json()
        except Exception as e:
            print(f"  ❌ 请求异常: {e}")
            writer.writerow({
                "意图编号": intent_id,
                "执行轮次": run_idx + 1,
                "步骤数": 0,
                "耗时(s)": -1,
                "是否成功": False
            })
            continue

        trace_id = data.get("trace_id")
        if not trace_id:
            print(f"  ⚠️ 缺失 trace_id，无法统计步骤数")
            writer.writerow({
                "意图编号": intent_id,
                "执行轮次": run_idx + 1,
                "步骤数": 0,
                "耗时(s)": -1,
                "是否成功": False
            })
            continue

        # 强制等待直到日志中出现 final_step=True
        entries = []
        print(f"  ⏳ 正在等待 trace_id={trace_id} 的 final_step 出现...")
        while True:
            entries = find_entries_by_trace_id(log_dir, trace_id)
            if any(e.get("final_step") is True for e in entries):
                print("  ✅ final_step 出现，准备记录结果并清理拓扑")
                break
            time.sleep(0.5)

        end_time = datetime.now()

        duration = round((end_time - start_time).total_seconds(), 3)

        step_count = len(entries)
        success = all(e.get("result") is True for e in entries)

        writer.writerow({
            "意图编号": intent_id,
            "执行轮次": run_idx + 1,
            "步骤数": step_count,
            "耗时(s)": duration,
            "是否成功": success
        })

        # 清空网络拓扑
        try:
            clear_resp = requests.post("http://localhost:5000/cleanup", timeout=30)
            if clear_resp.status_code == 200:
                print("  🧹 网络拓扑已清空")
            else:
                print(f"  ⚠️ 清理拓扑失败: {clear_resp.status_code}")
        except Exception as e:
            print(f"  ❌ 清理拓扑请求失败: {e}")

csvfile.close()
print(f"\n✅ 补测完成，结果已追加至：{output_path}")
