# 实验2修复意图执行成功率柱状图
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.patches import Patch
import os

# === 0. 自动查找最新 result2/exp2_test_* 文件夹 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# RESULT_DIR = os.path.join(BASE_DIR, "result2")
RESULT_DIR = BASE_DIR

# 找所有符合命名规则的子目录
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

# === 2. 颜色设定：红色 = 需要修复，灰色 = 不应修复 ===
colors = ["firebrick" if need else "lightgray" for need in df["need_repair"]]

# === 3. 绘图 ===
fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(df["intent_id"], df["intent_result_rate"], color=colors)

# === 4. 设置 Y 轴百分比格式 ===
ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))

# === 5. 在每根柱子顶部加百分比文字标签 ===
for bar, val in zip(bars, df["intent_result_rate"]):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, height + 0.02,
            f"{int(val * 100)}%", ha="center", va="bottom", fontsize=9)

# === 6. 添加分割线（区分修 vs 不修）===
ax.axvline(x=10.5, color="gray", linestyle="--")
ax.text(10.6, 1.05, "Intent 11–20 (should not need repair)", color="gray", fontsize=10)

# === 7. 设置图表样式 ===
ax.set_xlabel("Intent ID", fontsize=12)
ax.set_ylabel("Intent Result Success Rate", fontsize=12)
ax.set_title("Intent Execution Success Rate per Intent", fontsize=14)
ax.set_xticks(df["intent_id"])
ax.set_ylim(0, 1.2)

# === 8. 图例 ===
legend_elements = [
    Patch(facecolor="firebrick", label="Need Repair"),
    Patch(facecolor="lightgray", label="No Repair Needed")
]
ax.legend(handles=legend_elements)

# === 9. 保存图像 ===
plt.tight_layout()
output_path = os.path.join(latest_dir, "exp2_intent_result_rate.png")
plt.savefig(output_path, dpi=300)
print(f"📊 图像已保存至: {output_path}")
