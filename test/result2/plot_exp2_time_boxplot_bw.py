# ======== 实验2：修复意图与无需修复意图执行时间箱线图（黑白打印 + 中文） 图8========
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import os
import glob
import matplotlib.font_manager as fm
import matplotlib

# ======== 字体设置（服务器本地宋体） ========
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

# ======== 1. 查找并读取原始 exp2_*.csv 文件（非 processed） ========
csv_files = glob.glob(os.path.join(latest_dir, "exp2_*.csv"))
if not csv_files:
    raise RuntimeError("❌ 未找到 exp2_*.csv 文件")

raw_path = csv_files[0]
df = pd.read_csv(raw_path)

# ======== 2. 类型转换 ========
df["total_time"] = pd.to_numeric(df["total_time"], errors="coerce")

# ======== 3. 分类字段（前10个为需修复意图） ========
df["need_repair"] = df["intent_id"] <= 10

# ======== 4. 定义填充样式（黑白区分） ========
hatches = ["xx" if need else "//" for need in df.groupby("intent_id")["need_repair"].first()]

# ======== 5. 绘制箱线图 ========
fig, ax = plt.subplots(figsize=(14, 6))
box_data = [df[df["intent_id"] == i]["total_time"].dropna() for i in range(1, 21)]
box = ax.boxplot(
    box_data,
    patch_artist=True,
    widths=0.6,
    boxprops=dict(linewidth=1.2, color="black"),
    medianprops=dict(color="black", linewidth=1.2),
    whiskerprops=dict(color="black", linewidth=1),
    capprops=dict(color="black", linewidth=1),
)

# ======== 6. 为每个箱子设置黑白填充 ========
for patch, hatch in zip(box["boxes"], hatches):
    patch.set_facecolor("white")
    patch.set_edgecolor("black")
    patch.set_hatch(hatch)

# ======== 7. 坐标轴与标题 ========
ax.set_xlabel("意图编号", fontsize=12, fontproperties=prop)
ax.set_ylabel("总执行时间 /s", fontsize=12, fontproperties=prop)
ax.set_xticks(range(1, 21))
ax.set_xticklabels(range(1, 21), fontproperties=prop, fontsize=10)

# ✅ 要求：纵轴 & 横轴刻度短线朝内（同时不画顶部/右侧刻度）
ax.tick_params(axis="both", which="both", direction="in", top=False, right=False)

# ======== 8. 分割线与说明文字 ========
ax.axvline(x=10.5, color="gray", linestyle="--")
ymax = ax.get_ylim()[1]
ax.text(
    10.7, ymax * 0.95,
    "意图 11–20：不需要修复",
    color="gray",
    fontsize=10,
    fontproperties=prop
)

# ======== 9. 图例（黑白填充区分） ========
legend_elements = [
    Patch(facecolor='white', edgecolor='black', hatch='xxx', label='修复意图'),
    Patch(facecolor='white', edgecolor='black', hatch='/////', label='不需要修复意图')
]
ax.legend(
    handles=legend_elements,
    loc="upper left",
    frameon=True,
    prop=prop,
    fontsize=7
)

# ======== 10. 网格与边框样式 ========
ax.grid(axis="y", linestyle="--", alpha=0.6)
# ax.spines['top'].set_visible(False)
# ax.spines['right'].set_visible(False)

# ======== 11. 保存图像（PNG + SVG） ========
plt.tight_layout(rect=[0, 0, 0.85, 1])

output_png = os.path.join(latest_dir, "exp2_time_boxplot_bw.png")
output_svg = os.path.join(latest_dir, "exp2_time_boxplot_bw.svg")

plt.savefig(output_png, dpi=300, bbox_inches="tight")
plt.savefig(output_svg, format="svg", bbox_inches="tight")  # ✅ 额外保存 SVG
plt.close()

print(f"✅ 图表已保存至: {output_png}")
print(f"✅ SVG 图已保存至: {output_svg}")