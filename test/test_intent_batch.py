import requests
import time
import csv
import os

# 设置 API 地址
INTENT_API = "http://localhost:5000/intent"
STOP_API = "http://localhost:5000/stop"

# 文件路径
INTENT_FILE = "intent.txt"
RESULT_DIR = "result"
CSV_FILE = os.path.join(RESULT_DIR, "intent_test_results.csv")

# 创建 result 目录
os.makedirs(RESULT_DIR, exist_ok=True)

def load_intents(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def check_api_available(api_url):
    try:
        resp = requests.post(api_url, json={"intent": "创建一个包含 h1 和 h2 的网络拓扑"}, timeout=5)
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 无法连接到接口 {api_url}: {e}")
        return False

def clear_topology():
    try:
        resp = requests.post(STOP_API, timeout=5)
        print("🧹 拓扑清理结果:", resp.json().get("message", "未知响应"))
    except Exception as e:
        print(f"❌ 拓扑清理失败: {e}")

def test_intent(intent_text, repeat=5):
    success_count = 0
    durations = []

    for i in range(repeat):
        print(f"  - 第 {i+1} 次执行中...")
        start = time.time()
        try:
            resp = requests.post(INTENT_API, json={"intent": intent_text}, timeout=30)
            elapsed = round(time.time() - start, 4)
            durations.append(elapsed)
            if resp.status_code == 200 and resp.json().get("success") is True:
                success_count += 1
        except Exception as e:
            durations.append(-1)
            print(f"    ❌ 测试失败: {e}")
        finally:
            time.sleep(2)  # 稍作延迟
            clear_topology()

    avg_time = round(sum(d for d in durations if d >= 0) / max(1, len([d for d in durations if d >= 0])), 4)
    return success_count, avg_time, durations

def main():
    if not check_api_available(INTENT_API):
        print("❌ /intent 接口无法访问，请检查 Flask 是否启动")
        return

    intents = load_intents(INTENT_FILE)

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["意图", "成功次数", "平均耗时（秒）", "各次耗时"])

        for idx, intent in enumerate(intents, 1):
            print(f"\n[{idx}/{len(intents)}] 当前意图: {intent}")
            success, avg_time, durations = test_intent(intent)
            writer.writerow([intent, success, avg_time, durations])
            print(f"✅ 完成: 成功 {success}/5，平均耗时 {avg_time} 秒")

    print(f"\n🎉 全部测试完成，结果已保存至: {CSV_FILE}")

if __name__ == "__main__":
    main()
