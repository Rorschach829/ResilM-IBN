# ======== 实验2：修复动作触发成功率柱状图（黑白打印 + 中文） 图6========
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.patches import Patch
import os
import matplotlib.font_manager as fm
import matplotlib
from matplotlib.ticker import FuncFormatter  # ✅ 新增：0 不带 %

# ======== 字体设置（使用服务器本地宋体路径） ========
font_path = "/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf"  # 文鼎PL简报宋
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
matplotlib.rcParams['font.family'] = prop.get_name()
matplotlib.rcParams['axes.unicode_minus'] = False

# ✅ y 轴百分比格式：0 不带 %
def percent_no_zero(x, pos):
    if abs(x) < 1e-12:
        return "0"
    return f"{int(round(x * 100))}%"

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

# ======== 2. 将 repair_triggered_rate = -1 改为 0.0（未触发修复） ========
df.loc[df["repair_triggered_rate"] < 0, "repair_triggered_rate"] = 0.0

# ======== 3. 分配填充样式（黑白可区分） ========
def get_hatch(need_repair):
    return "xx" if need_repair else "//"

df["hatch"] = df["need_repair"].apply(get_hatch)

# ======== 4. 绘图 ========
fig, ax = plt.subplots(figsize=(12, 6))

bars = []
x_pos = range(len(df))
for i, row in enumerate(df.itertuples()):
    bar = ax.bar(
        i,
        row.repair_triggered_rate,
        color="white",
        edgecolor="black",
        hatch=row.hatch,
        linewidth=1.0
    )
    bars.append(bar)

# ======== 5. 添加百分比标签（柱顶文本仍保留 %，不影响“原点 0 不带 %”这个要求） ========
for i, row in enumerate(df.itertuples()):
    val = row.repair_triggered_rate
    ax.text(
        i,
        val + 0.02,
        f"{int(val * 100)}%",
        ha="center",
        va="bottom",
        fontsize=9,
        fontproperties=prop
    )

# ======== 6. 设置纵坐标为百分比格式（0 不带 %） ========
ax.yaxis.set_major_formatter(FuncFormatter(percent_no_zero))  # ✅ 替换 PercentFormatter
ax.set_ylim(0, 1.2)

# ✅ 要求：Y 轴短线朝内
ax.tick_params(axis="y", which="both", direction="in")

# ======== 7. 分隔线与说明文字 ========
ax.axvline(x=9.5, color="gray", linestyle="--")  # 假设前10条是需修复
ax.text(
    9.7, 1.05, "意图 11–20：不需要修复",
    color="gray", fontsize=10, fontproperties=prop
)

# ======== 8. 坐标轴与标题 ========
ax.set_xlabel("意图编号", fontsize=12, fontproperties=prop)
ax.set_ylabel("修复触发成功率", fontsize=12, fontproperties=prop)
ax.set_xticks(list(x_pos))
ax.set_xticklabels(df["intent_id"], fontproperties=prop, fontsize=10)
ax.grid(axis="y", linestyle="--", alpha=0.6)

# ✅ 要求：X 轴 1-10 去掉短线；11-20 短线朝内
# 注意：这里按“刻度位置索引”处理：0~9 对应意图 1~10，10~19 对应意图 11~20
ax.tick_params(axis="x", which="major", direction="in", bottom=True, top=False)
ticks = ax.xaxis.get_major_ticks()
for idx, t in enumerate(ticks):
    if idx <= 9:
        # 1-10：没有短线（但保留文字标签）
        t.tick1line.set_markersize(0)   # 底部刻度线长度=0
        t.tick2line.set_markersize(0)   # 顶部刻度线长度=0（保险）
    else:
        # 11-20：短线朝内
        t.tick1line.set_markersize(3.5)           # 给个可见长度
        t.tick1line.set_markeredgewidth(0.8)
        t.tick2line.set_markersize(0)             # 顶部不显示
# 再统一把后半段刻度方向设为 in（对 markerline 生效不强，主要靠上面 markersize）
# ax.tick_params(axis="x", which="major", direction="in")

# ======== 9. 图例（用不同填充线区分） ========
legend_elements = [
    Patch(facecolor='white', edgecolor='black', hatch='xxx', label='修复意图'),
    Patch(facecolor='white', edgecolor='black', hatch='/////', label='不需要修复意图')
]
# ax.legend(
#     handles=legend_elements,
#     loc="upper left",
#     bbox_to_anchor=(1.02, 1.0),
#     prop=prop,
#     fontsize=10
# )
ax.set_ylim(0, 1.18)   # 1.0 == 100%
ax.legend(
    handles=legend_elements,
    loc="upper left",
    frameon=True,
    prop=prop,
    fontsize=10
)

# ======== 10. 保存图像 ========
plt.tight_layout(rect=[0, 0, 0.85, 1])

output_png = os.path.join(latest_dir, "exp2_repair_triggered_rate_bw.png")
output_svg = os.path.join(latest_dir, "exp2_repair_triggered_rate_bw.svg")

plt.savefig(output_png, dpi=300, bbox_inches="tight")
plt.savefig(output_svg, format="svg", bbox_inches="tight")  # ✅ 新增 SVG

plt.close()

print(f"✅ PNG 图已保存至: {output_png}")
print(f"✅ SVG 图已保存至: {output_svg}")