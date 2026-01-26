import os
import pandas as pd

SUMMARY_FILE = "llm_summary.csv"   # 你刚才生成的汇总表
DS_FILE = "ds_chat.csv"            # 你已有的 DeepSeek 聚合表
OUTPUT_FILE = "llm_summary.csv"    # 直接覆盖写回（也可改成新文件名）

RUNS_PER_INTENT = 10
NUM_INTENTS = 15
TOTAL_RUNS = RUNS_PER_INTENT * NUM_INTENTS  # 150


def to_float(x):
    if x is None:
        return 0.0
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "none"}:
        return 0.0
    try:
        return float(s)
    except Exception:
        return 0.0


def normalize_success_rate(sr):
    """
    ds_chat.csv 的 success_rate 可能是：
    - 0~1 的比例（推荐）
    - 0~100 的百分比
    这里自动识别：>1 就当百分比处理。
    """
    sr = to_float(sr)
    if sr > 1.0:
        sr = sr / 100.0
    # 限幅一下，避免脏数据
    if sr < 0:
        sr = 0.0
    if sr > 1:
        sr = 1.0
    return sr


def compute_ds_row(ds_path: str) -> dict:
    df = pd.read_csv(ds_path)

    required = ["intent_id", "avg_time", "success_rate", "intent_token", "json_token"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"{ds_path} 缺少列 {c}，实际列：{list(df.columns)}")

    # 只取前15条（防止文件里多了别的）
    df = df.iloc[:NUM_INTENTS].copy()

    # 每条意图的成功次数 = success_rate * 10
    df["success_rate_norm"] = df["success_rate"].apply(normalize_success_rate)
    df["success_runs_intent"] = df["success_rate_norm"] * RUNS_PER_INTENT

    total_success_runs = df["success_runs_intent"].sum()

    # 总成功率：总成功次数 / 150
    success_rate = total_success_runs / float(TOTAL_RUNS)

    # 用“成功次数”作为权重做加权平均（只对成功样本定义的均值才合理）
    def weighted_avg(col_name: str) -> float:
        vals = df[col_name].apply(to_float)
        weights = df["success_runs_intent"]
        if total_success_runs <= 0:
            return 0.0
        return (vals * weights).sum() / total_success_runs

    avg_time = weighted_avg("avg_time")
    avg_intent_token = weighted_avg("intent_token")
    avg_json_token = weighted_avg("json_token")
    avg_token = avg_intent_token + avg_json_token

    return {
        "model": "ds_chat",  # 你也可以改成 deepseek-chat
        "total_runs": TOTAL_RUNS,
        "success_runs": int(round(total_success_runs)),
        "success_rate": round(success_rate, 4),
        "avg_time": round(avg_time, 3),
        "avg_intent_token": round(avg_intent_token, 2),
        "avg_json_token": round(avg_json_token, 2),
        "avg_token": round(avg_token, 2),
    }


def main():
    if not os.path.exists(SUMMARY_FILE):
        raise FileNotFoundError(f"找不到 {SUMMARY_FILE}（请在生成 llm_summary.csv 的目录运行）")
    if not os.path.exists(DS_FILE):
        raise FileNotFoundError(f"找不到 {DS_FILE}")

    summary = pd.read_csv(SUMMARY_FILE)
    ds_row = compute_ds_row(DS_FILE)

    # 如果 summary 里已经有 ds_chat，就先删掉再加（避免重复）
    if "model" in summary.columns:
        summary = summary[summary["model"].astype(str) != ds_row["model"]].copy()

    # 追加
    summary = pd.concat([summary, pd.DataFrame([ds_row])], ignore_index=True)

    # 列顺序对齐（如果你的 llm_summary.csv 列不同，这里会尽量保留）
    preferred_cols = [
        "model",
        "total_runs",
        "success_runs",
        "success_rate",
        "avg_time",
        "avg_intent_token",
        "avg_json_token",
        "avg_token",
    ]
    cols = [c for c in preferred_cols if c in summary.columns] + \
           [c for c in summary.columns if c not in preferred_cols]
    summary = summary[cols]

    summary.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    print(f"✅ 已将 ds_chat 汇总追加到 {OUTPUT_FILE}")
    print(ds_row)


if __name__ == "__main__":
    main()