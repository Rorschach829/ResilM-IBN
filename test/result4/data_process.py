import os
import csv
import pandas as pd

TOTAL_RUNS = 150  # 按你的定义固定为150（15条意图 * 10轮）

INPUT_FILES = [
    "GLM_nothink.csv",
    "GLM_think.csv",
    "kimi2.csv",
    "Qwen_plus.csv",
]

OUTPUT_FILE = "llm_summary.csv"


def to_number(x):
    """把 token / time 字段转成 float；空、None、非法都当 0。"""
    if x is None:
        return 0.0
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none"}:
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def summarize_one_csv(path: str, total_runs: int = TOTAL_RUNS) -> dict:
    df = pd.read_csv(path)

    # 容错：列名必须存在
    required_cols = ["avg_time", "is_successful", "intent_token", "json_token"]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"{path} 缺少列: {c}，实际列为: {list(df.columns)}")

    # 统一成功标记（去空格、大小写）
    success_mask = df["is_successful"].astype(str).str.strip().str.upper() == "Y"
    success_df = df[success_mask].copy()

    success_runs = int(success_df.shape[0])

    # 成功率按你要求：成功次数 / 150
    success_rate = success_runs / float(total_runs)

    # 只对成功样本算均值（成功次数为0则输出空/0）
    if success_runs > 0:
        avg_time = success_df["avg_time"].apply(to_number).sum() / success_runs
        avg_intent_token = success_df["intent_token"].apply(to_number).sum() / success_runs
        avg_json_token = success_df["json_token"].apply(to_number).sum() / success_runs
    else:
        avg_time = 0.0
        avg_intent_token = 0.0
        avg_json_token = 0.0

    avg_token = avg_intent_token + avg_json_token

    model_name = os.path.splitext(os.path.basename(path))[0]

    return {
        "model": model_name,
        "total_runs": total_runs,
        "success_runs": success_runs,
        "success_rate": round(success_rate, 4),       # 你也可以改成百分比
        "avg_time": round(avg_time, 3),               # 秒：保留3位小数够用
        "avg_intent_token": round(avg_intent_token, 2),
        "avg_json_token": round(avg_json_token, 2),
        "avg_token": round(avg_token, 2),
    }


def main():
    rows = []
    for f in INPUT_FILES:
        if not os.path.exists(f):
            raise FileNotFoundError(f"找不到文件: {f}（请确认脚本运行目录是否正确）")
        rows.append(summarize_one_csv(f, total_runs=TOTAL_RUNS))

    # 写出汇总 CSV
    fieldnames = [
        "model",
        "total_runs",
        "success_runs",
        "success_rate",
        "avg_time",
        "avg_intent_token",
        "avg_json_token",
        "avg_token",
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ 汇总完成: {OUTPUT_FILE}")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()