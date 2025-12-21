# ======== 实验2：修复意图与无需修复意图执行平均时间对比图（黑白打印 + 中文） ========
import pandas as pd
import matplotlib.pyplot as plt
import os
import matplotlib.font_manager as fm
import matplotlib
from matplotlib.patches import Patch

# ======== 字体设置（服务器宋体） ========
font_path = "/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf"  # 文鼎PL简报宋
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
matplotlib.rcParams['font.family'] = prop.get_name()
matplotlib.rcParams['axes.unicode_minus'] = False

# ======== 0. 自动查找最新 exp2_test_* 文件夹 ========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

# ======== 1. 读取处理后的数据 ========
csv_path = os.path.join(latest_dir, "exp2_processed.csv")
if not os.path.exists(csv_path):
    raise RuntimeError("❌ 未找到 exp2_processed.csv 文件")
df = pd.read_csv(csv_path)

# ======== 2. 添加分类字段 ========
df["group"] = df["need_repair"].map({True: "需修复意图", False: "无需修复意图"})

# ======== 3. 按分类计算平均耗时 ========
grouped_avg = df.groupby("group")["avg_time"].mean().reset_index()

# ======== 4. 分配填充样式（黑白区分） ========
def get_hatch(group_name):
    return "xx" if "需修复" in group_name else "//"

grouped_avg["hatch"] = grouped_avg["group"].apply(get_hatch)

# ======== 5. 绘图 ========
fig, ax = plt.subplots(figsize=(8, 5))
bars = []
x_pos = range(len(grouped_avg))

for i, row in enumerate(grouped_avg.itertuples()):
    bar = ax.bar(
        i,
        row.avg_time,
        color="white",
        edgecolor="black",
        hatch=row.hatch,
        linewidth=1.0,
        width=0.5
    )
    bars.append(bar)

# ======== 6. 添加柱顶标签 ========
for i, row in enumerate(grouped_avg.itertuples()):
    ax.text(
        i,
        row.avg_time + 0.2,
        f"{row.avg_time:.1f} s",
        ha="center",
        va="bottom",
        fontsize=10,
        fontproperties=prop
    )

# ======== 7. 坐标轴与标题 ========
ax.set_xticks(x_pos)
ax.set_xticklabels(grouped_avg["group"], fontproperties=prop, fontsize=11)
ax.set_ylabel("平均执行时间（秒）", fontsize=12, fontproperties=prop)
# ax.set_title("实验2：修复意图与无需修复意图的平均执行时间对比", fontsize=14, fontproperties=prop)
ax.set_ylim(grouped_avg["avg_time"].min() * 0.9, grouped_avg["avg_time"].max() * 1.15)

# ======== 8. 图例 ========
legend_elements = [
    Patch(facecolor='white', edgecolor='black', hatch='xx', label='需修复意图'),
    Patch(facecolor='white', edgecolor='black', hatch='//', label='无需修复意图')
]
ax.legend(
    handles=legend_elements,
    loc="upper right",
    prop=prop,
    fontsize=10
)

# ======== 9. 样式调整 ========
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.grid(axis="y", linestyle="--", alpha=0.6)

# ======== 10. 保存图像 ========
plt.tight_layout()
output_path = os.path.join(latest_dir, "exp2_avg_time_grouped_bw.png")
plt.savefig(output_path, dpi=300, bbox_inches="tight")
plt.close()

print(f"✅ 图表已保存至: {output_path}")