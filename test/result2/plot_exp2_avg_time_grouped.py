# 修复意图与无需修复意图执行平均时间对比图
import pandas as pd
import matplotlib.pyplot as plt
import os
import glob

# === 0. 自动查找最新 result2/exp2_test_* 文件夹 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# RESULT_DIR = os.path.join(BASE_DIR, "result2")
RESULT_DIR = BASE_DIR

subdirs = [
    os.path.join(RESULT_DIR, d)
    for d in os.listdir(RESULT_DIR)
    if d.startswith("exp2_test_") and os.path.isdir(os.path.join(RESULT_DIR, d))
]

if not subdirs:
    raise RuntimeError("❌ 未找到任何 exp2_test_* 文件夹")

latest_dir = max(subdirs, key=os.path.getmtime)
print(f"✅ 最新实验目录为: {latest_dir}")

# === 1. 读取处理后的数据 ===
csv_path = os.path.join(latest_dir, "exp2_processed.csv")
if not os.path.exists(csv_path):
    raise RuntimeError("❌ 未找到 exp2_processed.csv 文件")
df = pd.read_csv(csv_path)

# === 2. 添加分类字段 ===
df["group"] = df["need_repair"].map({True: "Need Repair", False: "No Repair"})

# === 3. 按分类计算平均耗时 ===
grouped_avg = df.groupby("group")["avg_time"].mean().reset_index()

# === 4. 配色（红 = 需修复，灰 = 不修复）===
colors = ["firebrick" if g == "Need Repair" else "lightgray" for g in grouped_avg["group"]]

# === 5. 绘图 ===
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(grouped_avg["group"], grouped_avg["avg_time"], color=colors, width=0.5)

# === 6. 添加柱上标签 ===
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, height + 0.5,
            f"{height:.1f} s", ha="center", va="bottom", fontsize=11)

# === 7. 图表设置 ===
ax.set_ylabel("Average Execution Time (seconds)", fontsize=12)
ax.set_title("Average Execution Time: Repair vs No Repair", fontsize=14)
ax.set_ylim(20, 26)  # 可调节显示范围

# === 8. 去掉多余边框 ===
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)

# === 9. 保存图像 ===
plt.tight_layout()
output_path = os.path.join(latest_dir, "exp2_avg_time_grouped.png")
plt.savefig(output_path, dpi=300)
print(f"📊 图像已保存至: {output_path}")
