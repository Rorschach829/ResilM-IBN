import pandas as pd
import matplotlib.pyplot as plt

# === 1. 读取处理后的数据 ===
df = pd.read_csv("exp2_processed.csv")  # 替换为你的路径

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
# ax.set_ylim(0, max(grouped_avg["avg_time"]) * 1.3)
ax.set_ylim(20, 26)  # 你可以根据数据具体调，比如 17 到 28，更聚焦差异


# === 8. 去掉多余边框 ===
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)

# === 9. 保存图像 ===
plt.tight_layout()
plt.savefig("exp2_avg_time_grouped.png", dpi=300)
# plt.show()  # 调试时打开
