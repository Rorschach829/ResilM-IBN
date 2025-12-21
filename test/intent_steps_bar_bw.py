# ======== 意图复杂度统计图（黑白打印版） ========
import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
from matplotlib.patches import Patch
import matplotlib.font_manager as fm
import matplotlib

# ======== 字体设置（使用服务器指定字体路径） ========
font_path = "/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf"  # 文鼎PL简报宋
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
matplotlib.rcParams['font.family'] = prop.get_name()
matplotlib.rcParams['axes.unicode_minus'] = False

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
df = df.sort_values(by="intent_id")

# ======== 第三步：根据步骤数量划分复杂度等级并分配填充样式 ========
def get_hatch(steps):
    if steps <= 3:
        return "//"   # 低复杂度
    elif steps <= 6:
        return "\\"   # 中复杂度
    else:
        return "xx"   # 高复杂度

df["hatch"] = df["steps"].apply(get_hatch)

# ======== 第四步：绘图 ========
fig, ax = plt.subplots(figsize=(10, 6))

bars = []
x_pos = range(len(df))
for i, row in enumerate(df.itertuples()):
    bar = ax.bar(
        i,
        row.steps,
        color="white",
        edgecolor="black",
        hatch=row.hatch,
        linewidth=1.0
    )
    bars.append(bar)

# 设置 X 轴刻度与标签
ax.set_xticks(x_pos)
ax.set_xticklabels(df["intent_id"], fontproperties=prop, fontsize=10)

# 添加数值标签
for i, row in enumerate(df.itertuples()):
    ax.text(
        i,
        row.steps + 0.2,
        f"{int(row.steps)}",
        ha='center',
        va='bottom',
        fontsize=9,
        fontproperties=prop
    )

# ======== 设置坐标轴与标题 ========
ax.set_xlabel("意图编号", fontproperties=prop, fontsize=12)
ax.set_ylabel("执行步骤数", fontproperties=prop, fontsize=12)
ax.set_title("意图复杂度分布（填充样式表示复杂度等级）", fontproperties=prop, fontsize=13)
ax.grid(axis='y', linestyle='--', alpha=0.6)

# ======== 图例说明 ========
legend_elements = [
    Patch(facecolor='white', edgecolor='black', hatch='//', label='低复杂度（步骤 ≤ 3）'),
    Patch(facecolor='white', edgecolor='black', hatch='\\', label='中复杂度（3 < 步骤 ≤ 6）'),
    Patch(facecolor='white', edgecolor='black', hatch='xx', label='高复杂度（步骤 > 6）')
]
ax.legend(
    handles=legend_elements,
    loc="upper left",
    bbox_to_anchor=(1.02, 1.0),
    prop=prop,
    fontsize=10
)

# ======== 布局与保存 ========
plt.tight_layout(rect=[0, 0, 0.85, 1])
output_path = os.path.join(latest_dir, "intent_steps_bar_bw.png")
plt.savefig(output_path, dpi=300, bbox_inches="tight")
plt.close()

print(f"✅ 图表已保存至: {output_path}")