import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.patches import Patch

# === 1. 读取处理后的数据 ===
df = pd.read_csv("exp2_processed.csv")  # 修改为你的路径

# === 2. 将 repair_triggered_rate = -1 改为 0（不触发修复）===
df.loc[df["repair_triggered_rate"] < 0, "repair_triggered_rate"] = 0.0

# === 3. 设置颜色：红色 = 应修复，灰色 = 不应修复 ===
colors = ["firebrick" if need else "lightgray" for need in df["need_repair"]]

# === 4. 创建图表 ===
fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.bar(df["intent_id"], df["repair_triggered_rate"], color=colors)
# === 在每根柱子上方加标签（显示百分比）===
for bar, val in zip(bars, df["repair_triggered_rate"]):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, height + 0.02,
            f"{int(val * 100)}%", ha="center", va="bottom", fontsize=9)


# === 5. 设置纵坐标为百分比格式 ===
ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))

# === 6. 添加灰色分割线 & 注释 ===
ax.axvline(x=10.5, color="gray", linestyle="--")
ax.text(10.6, 1.05, "Intent 11–20 (should not trigger repair)", color="gray", fontsize=10)

# === 7. 图表样式设置 ===
ax.set_xlabel("Intent ID", fontsize=12)
ax.set_ylabel("Repair Triggered Rate", fontsize=12)
ax.set_title("Repair Triggered Rate per Intent", fontsize=14)
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
plt.savefig("exp2_repair_triggered_rate.png", dpi=300)
# plt.show()  # 可用于调试
