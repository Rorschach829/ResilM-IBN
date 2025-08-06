import pandas as pd

# === 1. 加载原始数据 ===
df = pd.read_csv("exp2.csv")  # 替换为你的实际路径，如 "./result2/exp2.csv"

# === 2. 转换布尔字段（如为字符串） ===
bool_cols = ["repair_triggered", "is_ping_success_before", "repair_success", "final_result"]
for col in bool_cols:
    df[col] = df[col].astype(str).str.lower().map({"true": True, "false": False})

# === 3. 添加 need_repair 字段（intent_id 1-10） ===
df["need_repair"] = df["intent_id"] <= 10

# === 4. 计算每轮的 intent_result 字段 ===
def compute_intent_result(row):
    if row["intent_id"] <= 10:
        return (
            row["is_ping_success_before"] is False
            and row["repair_triggered"] is True
            and row["final_result"] is True
        )
    else:
        return (
            row["is_ping_success_before"] is True
            and row["repair_triggered"] is False
            and row["final_result"] is True
        )

df["intent_result"] = df.apply(compute_intent_result, axis=1)

# === 5. 聚合处理，计算 repair_triggered_rate、intent_result_rate、avg_time ===
grouped = df.groupby(["intent_id", "host_pair"]).agg({
    "need_repair": "first",
    "repair_triggered": "mean",
    "intent_result": "mean",
    "total_time": "mean"
}).reset_index()

# === 6. 对 intent_id > 10 的行修正 repair_triggered_rate = -1 ===
grouped.loc[grouped["intent_id"] > 10, "repair_triggered"] = -1

# === 7. 重命名字段 ===
processed = grouped.rename(columns={
    "repair_triggered": "repair_triggered_rate",
    "intent_result": "intent_result_rate",
    "total_time": "avg_time"
})

# === 8. 保存到 CSV 文件 ===
processed.to_csv("exp2_processed.csv", index=False)
print("✅ 处理完成，文件已保存为 exp2_processed.csv")
