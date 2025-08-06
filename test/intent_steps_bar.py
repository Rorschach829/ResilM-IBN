import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

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

# ======== 第三步：归一化 steps → 颜色深浅（Blues colormap，跳过最浅区） ========
steps = df["steps"].astype(float)
normed_steps = (steps - steps.min()) / (steps.max() - steps.min())
base_cmap = cm.Blues
colors = base_cmap(0.4 + 0.6 * normed_steps)  # 映射到 [0.4, 1.0] 避免太浅

# ======== 第四步：绘图 ========
sns.set(style="whitegrid", font_scale=1.2)
df = df.sort_values(by="intent_id")

fig, ax = plt.subplots(figsize=(10, 6))
# bars = ax.bar(df["intent_id"], df["steps"], color=colors)
x_pos = range(len(df))  # 明确使用索引位置
bars = ax.bar(x_pos, df["steps"], color=colors)
ax.set_xticks(x_pos)  # 设置刻度位置
ax.set_xticklabels(df["intent_id"])  # 设置对应标签


# 添加标签
for index, row in df.iterrows():
    ax.text(index, row.steps + 0.2, f"{int(row.steps)}", ha='center', va='bottom', fontsize=10)

# 设置标签与标题
ax.set_xlabel("Intent ID")
ax.set_ylabel("Number of Steps")
ax.set_title("Intent Complexity (Darker Color Indicates More Steps)")

# ======== 添加 colorbar 图例 ========
norm = Normalize(vmin=steps.min(), vmax=steps.max())
sm = ScalarMappable(cmap=cm.Blues, norm=norm)
sm.set_array([])  # dummy array for colorbar
cbar = plt.colorbar(sm, ax=ax, pad=0.02)
cbar.set_label("Number of Steps (Color Mapping)")

# 保存图像
plt.tight_layout()
output_path = os.path.join(latest_dir, "intent_steps_bar_colormapped.png")
plt.savefig(output_path, dpi=300)
plt.close()

print(f"✅ 已保存图像（含颜色图例）: {output_path}")
