# ======== 实验2：修复意图执行成功率柱状图（黑白打印 + 中文） ========
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.patches import Patch
import os
import matplotlib.font_manager as fm
import matplotlib

# ======== 字体设置（服务器本地宋体路径） ========
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

# ======== 2. 分配填充样式（黑白区分） ========
def get_hatch(need_repair):
    return "xx" if need_repair else "//"

df["hatch"] = df["need_repair"].apply(get_hatch)

# ======== 3. 绘图 ========
fig, ax = plt.subplots(figsize=(12, 6))

bars = []
x_pos = range(len(df))
for i, row in enumerate(df.itertuples()):
    bar = ax.bar(
        i,
        row.intent_result_rate,
        color="white",
        edgecolor="black",
        hatch=row.hatch,
        linewidth=1.0
    )
    bars.append(bar)

# ======== 4. 设置 Y 轴为百分比格式 ========
ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
ax.set_ylim(0, 1.2)

# ======== 5. 在柱顶添加百分比文字标签 ========
for i, row in enumerate(df.itertuples()):
    val = row.intent_result_rate
    ax.text(
        i,
        val + 0.02,
        f"{int(val * 100)}%",
        ha="center",
        va="bottom",
        fontsize=9,
        fontproperties=prop
    )

# ======== 6. 添加分割线与说明文字 ========
ax.axvline(x=9.5, color="gray", linestyle="--")
ax.text(
    9.7, 1.05,
    "意图 11–20：无需修复",
    color="gray",
    fontsize=10,
    fontproperties=prop
)

# ======== 7. 坐标轴与标题 ========
ax.set_xlabel("意图编号", fontsize=12, fontproperties=prop)
ax.set_ylabel("执行成功率", fontsize=12, fontproperties=prop)
# ax.set_title("实验2：修复后意图执行成功率", fontsize=14, fontproperties=prop)
ax.set_xticks(x_pos)
ax.set_xticklabels(df["intent_id"], fontproperties=prop, fontsize=10)
ax.grid(axis="y", linestyle="--", alpha=0.6)

# ======== 8. 图例（黑白填充样式） ========
legend_elements = [
    Patch(facecolor='white', edgecolor='black', hatch='xx', label='需修复意图'),
    Patch(facecolor='white', edgecolor='black', hatch='//', label='无需修复意图')
]
ax.legend(
    handles=legend_elements,
    loc="upper left",
    bbox_to_anchor=(1.02, 1.0),
    prop=prop,
    fontsize=10
)

# ======== 9. 保存图像 ========
plt.tight_layout(rect=[0, 0, 0.85, 1])
output_path = os.path.join(latest_dir, "exp2_intent_result_rate_bw.png")
plt.savefig(output_path, dpi=300, bbox_inches="tight")
plt.close()

print(f"✅ 图表已保存至: {output_path}")