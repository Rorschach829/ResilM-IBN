import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.patches import Patch

# === 1. 读取处理后的数据 ===
df = pd.read_csv("exp2_processed.csv")  # 替换为你的路径

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
plt.savefig("exp2_intent_result_rate.png", dpi=300)
# plt.show()  # 调试用
