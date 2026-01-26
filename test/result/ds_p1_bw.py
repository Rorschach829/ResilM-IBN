import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import os
import matplotlib
import matplotlib.font_manager as fm
from matplotlib.ticker import FuncFormatter

# ======================
# 字体配置（按你给的）
# ======================
cn_font_path = "/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf"
fm.fontManager.addfont(cn_font_path)
cn_prop = fm.FontProperties(fname=cn_font_path)

tnr_font_path = "/data/gjw/Times New Roman.ttf"
fm.fontManager.addfont(tnr_font_path)
tnr_prop = fm.FontProperties(fname=tnr_font_path)

matplotlib.rcParams["font.family"] = [
    cn_prop.get_name(),
    tnr_prop.get_name()
]
matplotlib.rcParams["axes.unicode_minus"] = False

matplotlib.rcParams.update({
    "font.size": 6.5,
    "axes.titlesize": 6.5,
    "axes.labelsize": 6.5,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6,
})

print("✅ 字体与字号配置完成")

# ======================
# 读取当前目录下的数据文件
# ======================
CSV_FILE = "ds_summary.csv"   # ← 当前目录

if not os.path.exists(CSV_FILE):
    raise RuntimeError(f"❌ 未找到数据文件: {CSV_FILE}")

df = pd.read_csv(CSV_FILE)
print(f"✅ 成功读取 {len(df)} 条数据")

# 需要的列检查
required_cols = ["intent_id", "hosts", "avg_time", "success_rate"]
for col in required_cols:
    if col not in df.columns:
        raise RuntimeError(f"❌ CSV 缺少必要列: {col}")

# 数据类型处理
df["intent_id"] = pd.to_numeric(df["intent_id"])
df["hosts"] = pd.to_numeric(df["hosts"])
df["avg_time"] = pd.to_numeric(df["avg_time"])
df["success_rate"] = pd.to_numeric(df["success_rate"])
df = df.sort_values("intent_id").reset_index(drop=True)

# ======================
# hatch 规则
# ======================
def get_hatch(hosts):
    if hosts < 4:
        return "//"
    elif hosts < 10:
        return "\\"
    else:
        return "xx"

df["hatch"] = df["hosts"].apply(get_hatch)

# ======================
# 右轴百分号格式：0 不加 %
# ======================
def percent_formatter(x, pos):
    # 兼容浮点误差
    if abs(x) < 1e-9:
        return "0"
    return f"{int(round(x))}%"

# ======================
# 绘图
# ======================
fig, ax1 = plt.subplots(figsize=(14 / 2.54, 6 / 2.54))  # cm → inch（期刊友好）

bars = []
for _, row in df.iterrows():
    bar = ax1.bar(
        row["intent_id"],
        row["avg_time"],
        color="white",
        edgecolor="black",
        hatch=row["hatch"],
        linewidth=0.8
    )
    bars.append(bar)

ax1.set_xlabel("意图编号")

# ✅ 编辑要求：左侧纵坐标改为“平均执行时间  /s”
ax1.set_ylabel("平均执行时间  /s")

ax1.set_ylim(0, df["avg_time"].max() * 1.2)
ax1.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)

# ✅ 编辑要求：坐标轴短线（刻度线）放在坐标内侧
ax1.tick_params(axis="x", length=0,which="both", direction="in", right=True)

# 柱顶标注（时间值，不需要加单位）
for idx, bar_group in enumerate(bars):
    bar = bar_group[0]
    h = bar.get_height()

    # 基础偏移
    offset = df["avg_time"].max() * 0.02

    # ✅ 只对第 15 号意图单独上移（注意 intent_id 从 1 开始）
    if df.loc[idx, "intent_id"] == 15:
        offset = df["avg_time"].max() * 0.07   # 抬高一点点即可

    ax1.text(
        bar.get_x() + bar.get_width() / 2,
        h + offset,
        f"{h:.1f}",
        ha="center",
        va="bottom",
        fontsize=7
    )
# for bar_group in bars:
#     bar = bar_group[0]
#     h = bar.get_height()
#     ax1.text(
#         bar.get_x() + bar.get_width() / 2,
#         h + df["avg_time"].max() * 0.02,
#         f"{h:.1f}",
#         ha="center",
#         va="bottom",
#         fontsize=7
#     )

# ======================
# 右轴：成功率
# ======================
ax2 = ax1.twinx()
ax2.scatter(
    df["intent_id"],
    df["success_rate"],
    facecolors="white",
    edgecolors="black",
    s=20,
    linewidths=0.8
)

# ✅ 编辑要求：右侧纵坐标的 % 不写在轴标题里
ax2.set_ylabel("执行成功率")

ax2.set_ylim(0, 110)

# ✅ 编辑要求：右侧纵坐标刻度值带 %（0 不带）
ax2.yaxis.set_major_formatter(FuncFormatter(percent_formatter))

# ✅ 编辑要求：坐标轴短线放在坐标内侧（右轴同样）
ax2.tick_params(axis="y", which="both", direction="in")

# ✅ 编辑要求：右侧数据标注带 %（0 不带）
# （你右轴是散点，不是柱；但编辑要的是“对应右轴的数据数值带%”，按等价处理）
# for x, y in zip(df["intent_id"], df["success_rate"]):
#     if abs(y) < 1e-9:
#         label = "0"
#     else:
#         label = f"{y:.1f}%"
#     ax2.text(
#         x,
#         y + 2.0,          # 稍微上移避免遮挡
#         label,
#         ha="center",
#         va="bottom",
#         fontsize=7
#     )

ax1.set_xticks(df["intent_id"])
ax1.set_xticklabels(df["intent_id"].astype(int))

# ✅ 保险：x 轴刻度线也朝内
ax1.tick_params(axis="x", which="both", direction="in")
ax1.tick_params(axis="y", which="both", direction="in")
# ======================
# 图例（图内，纵向）
# ======================
legend_elements = [
    Patch(facecolor="white", edgecolor="black", hatch="////", label="小型拓扑"),
    Patch(facecolor="white", edgecolor="black", hatch="\\\\\\\\\\", label="中型拓扑"),
    Patch(facecolor="white", edgecolor="black", hatch="xxxx", label="大型拓扑"),
    Patch(facecolor="white", edgecolor="black", label="平均执行时间"),
    Line2D([0], [0], color="black", marker="o", linestyle="None",
           markerfacecolor="white", markeredgecolor="black", label="执行成功率"),
]

ax1.legend(
    handles=legend_elements,
    loc="lower left",
    bbox_to_anchor=(0.02, 0.4),
    frameon=True,
    edgecolor="black"
)

# 标题
plt.title("不同拓扑规模下的意图执行时间与成功率")

# ======================
# 保存 SVG / PNG
# ======================
plt.tight_layout(rect=[0, 0, 0.82, 1])
out_svg = "intent_time_success_bw.svg"
out_png = "intent_time_success_bw.png"

plt.savefig(out_svg, format="svg", bbox_inches="tight")
plt.savefig(out_png, dpi=300, format="png", bbox_inches="tight")
print(f"✅ SVG 图已保存为: {out_svg}")

plt.close()