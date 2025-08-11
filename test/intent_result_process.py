import pandas as pd
import os
import glob

# ======== 第一步：定位最新创建的子文件夹 ========
RESULT_BASE_DIR = "result"
subdirs = [os.path.join(RESULT_BASE_DIR, d) for d in os.listdir(RESULT_BASE_DIR) if os.path.isdir(os.path.join(RESULT_BASE_DIR, d))]

if not subdirs:
    raise RuntimeError("❌ 未找到任何子文件夹")

latest_dir = max(subdirs, key=os.path.getmtime)
print(f"✅ 最新结果文件夹为: {latest_dir}")

# ======== 第二步：查找 intent_summary_*.csv 文件 ========
pattern = os.path.join(latest_dir, "intent_summary_*.csv")
summary_files = glob.glob(pattern)

if not summary_files:
    raise RuntimeError("❌ 最新文件夹中未找到 intent_summary_*.csv 文件")

latest_summary = summary_files[0]
print(f"✅ 找到意图汇总文件: {latest_summary}")

# ======== 第三步：处理数据并保存 ========
# 读取数据
df = pd.read_csv(latest_summary)

# 成功列转换为布尔值
df["成功"] = df["成功"].map(lambda x: 1 if str(x).strip() == "是" else 0)

# 分组计算统计指标
summary = df.groupby("编号").agg(
    steps=("步骤数", lambda x: round(x.mean())),
    avg_time=("耗时(秒)", lambda x: round(x[pd.to_numeric(x, errors='coerce') >= 0].astype(float).mean(), 1)),
    success_rate=("成功", "mean")
).reset_index()

# 重命名列名
summary = summary.rename(columns={"编号": "intent_id"})
summary["success_rate"] = (summary["success_rate"] * 100).round(2)

# 保存结果
output_path = os.path.join(latest_dir, "intent_data_processed.csv")
summary.to_csv(output_path, index=False)

print(f"🎉 数据处理完成，结果保存为: {output_path}")

