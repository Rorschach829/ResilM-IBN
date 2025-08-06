import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# === 1. 读取原始每轮数据（非 processed） ===
df = pd.read_csv("exp2.csv")  # 修改为你的实际路径

# === 2. 类型转换（确保 total_time 为 float）===
df["total_time"] = pd.to_numeric(df["total_time"], errors="coerce")

# === 3. 设置颜色（根据 need_repair 分类）===
df["need_repair"] = df["intent_id"] <= 10
colors = ["firebrick" if need else "lightgray" for need in df.groupby("intent_id")["need_repair"].first()]

# === 4. 创建箱线图 ===
fig, ax = plt.subplots(figsize=(14, 6))

# 箱线图数据结构：每个 intent_id 一组 total_time
box_data = [df[df["intent_id"] == i]["total_time"].dropna() for i in range(1, 21)]
box = ax.boxplot(box_data, patch_artist=True)

# === 5. 着色每个箱子 ===
for patch, color in zip(box["boxes"], colors):
    patch.set_facecolor(color)
for median in box["medians"]:
    median.set_color("black")

# === 6. 添加图表信息 ===
ax.set_title("Intent Execution Time Distribution (Boxplot)", fontsize=14)
ax.set_xlabel("Intent ID", fontsize=12)
ax.set_ylabel("Total Execution Time (seconds)", fontsize=12)
ax.set_xticks(range(1, 21))
ax.set_xticklabels(range(1, 21))

# 分割线标明 intent 11~20
ax.axvline(x=10.5, color="gray", linestyle="--")
ax.text(10.6, ax.get_ylim()[1] * 0.95, "Intent 11–20 (No Repair Needed)", color="gray", fontsize=10)

# 图例
legend_elements = [
    Patch(facecolor="firebrick", label="Need Repair"),
    Patch(facecolor="lightgray", label="No Repair Needed")
]
ax.legend(handles=legend_elements)

# === 7. 保存图像 ===
plt.tight_layout()
plt.savefig("exp2_time_boxplot.png", dpi=300)
# plt.show()  # 可调试时使用
