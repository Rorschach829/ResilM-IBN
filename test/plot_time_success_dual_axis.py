import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import os
import glob

# ======== 第一步：定位最新创建的子文件夹 ========
RESULT_BASE_DIR = "result"
subdirs = [
    os.path.join(RESULT_BASE_DIR, d)
    for d in os.listdir(RESULT_BASE_DIR)
    if os.path.isdir(os.path.join(RESULT_BASE_DIR, d))
]

if not subdirs:
    raise RuntimeError("❌ 未找到任何子文件夹")

latest_dir = max(subdirs, key=os.path.getmtime)
print(f"✅ 最新结果文件夹为: {latest_dir}")

# ======== 第二步：读取 intent_data_processed.csv 文件 ========
csv_file = os.path.join(latest_dir, "intent_data_processed.csv")
if not os.path.exists(csv_file):
    raise RuntimeError("❌ 未找到 intent_data_processed.csv 文件")

df = pd.read_csv(csv_file)
print(f"✅ 成功读取数据，共 {len(df)} 条意图")

# ======== 第三步：根据 hosts 列分配颜色 ========
def get_color(hosts):
    if hosts < 4:
        return "green"
    elif hosts < 10:
        return "blue"
    else:
        return "red"

df["color"] = df["hosts"].apply(get_color)

# ======== 第四步：绘图并保存 ========
fig, ax1 = plt.subplots(figsize=(14, 6))

# 左轴：平均耗时柱状图
bars = ax1.bar(df["intent_id"], df["avg_time"], color=df["color"])
ax1.set_xlabel("Intent ID")
ax1.set_ylabel("Average Execution Time (s)", color="black")
ax1.tick_params(axis="y", labelcolor="black")
ax1.set_ylim(0, df["avg_time"].max() * 1.2)
ax1.grid(axis="y", linestyle="--", alpha=0.6)

for bar in bars:
    height = bar.get_height()
    ax1.text(
        bar.get_x() + bar.get_width() / 2,
        height + 0.5,  # 调高一点避免遮挡柱子
        f"{height:.1f}",
        ha="center",
        va="bottom",
        fontsize=9,
        color="black"
    )


# 右轴：成功率折线图
ax2 = ax1.twinx()
ax2.plot(df["intent_id"], df["success_rate"], color="black", marker="o", linewidth=2)
ax2.set_ylabel("Success Rate (%)", color="black")
ax2.tick_params(axis="y", labelcolor="black")
ax2.set_ylim(0, 110)

# X 轴标签
plt.xticks(ticks=df["intent_id"], labels=df["intent_id"], fontsize=10)

# 图例
legend_elements = [
    Patch(facecolor='green', label='Small Topology (hosts < 4)'),
    Patch(facecolor='blue', label='Medium Topology (4 ≤ hosts < 10)'),
    Patch(facecolor='red', label='Large Topology (hosts ≥ 10)'),
    Patch(facecolor='gray', label='Avg Time (bar)'),
    Patch(facecolor='white', edgecolor='black', label='Success Rate (line)', linewidth=2)
]
plt.legend(
    handles=legend_elements,
    loc="upper left",
    bbox_to_anchor=(1.18, 1.0)
)

# 图标题
plt.title("Intent Execution Time and Success Rate by Topology Size")

# 布局和保存
plt.tight_layout(rect=[0, 0, 0.82, 1])
output_path = os.path.join(latest_dir, "intent_time_success_combined.png")
plt.savefig(output_path, dpi=300)
print(f"✅ 图表已保存至: {output_path}")


