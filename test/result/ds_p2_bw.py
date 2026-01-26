import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib.patches import Patch
import matplotlib.font_manager as fm
import matplotlib

# ======================
# 字体设置（统一：中文 + Times New Roman）
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
# 读取当前目录 ds_summary.csv
# ======================
csv_file = "ds_summary.csv"
if not os.path.exists(csv_file):
    raise RuntimeError(f"❌ 未找到 {csv_file}（请确认在当前目录）")

df = pd.read_csv(csv_file)

required_cols = ["intent_id", "steps"]
for c in required_cols:
    if c not in df.columns:
        raise RuntimeError(f"❌ {csv_file} 缺少必要列: {c}，实际列: {list(df.columns)}")

df["intent_id"] = pd.to_numeric(df["intent_id"], errors="coerce")
df["steps"] = pd.to_numeric(df["steps"], errors="coerce")
df = df.dropna(subset=["intent_id", "steps"]).sort_values("intent_id").reset_index(drop=True)

# steps 可能是浮点（比如均值），这里画“复杂度”建议用四舍五入到最接近整数
df["steps_int"] = df["steps"].round().astype(int)

print(f"✅ 成功读取数据：{len(df)} 条意图")

# ======================
# 复杂度 hatch 规则（与之前一致）
# ======================
def get_hatch(steps_int: int) -> str:
    if steps_int <= 3:
        return "//"   # 低复杂度
    elif steps_int <= 6:
        return "\\"   # 中复杂度
    else:
        return "xx"   # 高复杂度

df["hatch"] = df["steps_int"].apply(get_hatch)

# ======================
# 绘图（统一风格：黑白 + 网格 + 线宽）
# ======================
fig, ax = plt.subplots(figsize=(14/2.54, 6/2.54))

n = len(df)
x_pos = np.arange(n) * 1
bar_width = 0.65

for i, row in enumerate(df.itertuples(index=False)):
    ax.bar(
        x_pos[i],
        row.steps_int,
        width=bar_width,
        color="white",
        edgecolor="black",
        hatch=df.loc[i, "hatch"],
        linewidth=0.8
    )

# 坐标轴标签
ax.set_xlabel("意图编号")
ax.set_ylabel("执行步骤数 /steps")
ax.set_title("意图复杂度分布（填充样式表示复杂度等级）")

# X 轴刻度
ax.set_xticks(x_pos)
ax.set_xticklabels(df["intent_id"].astype(int))

# Y 轴范围
y_max = max(df["steps_int"].max(), 1)
ax.set_ylim(0, y_max * 1.25)

# 网格
ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.6)

# ✅ 审稿人要求：刻度短线放在坐标内侧（关键改动）
ax.tick_params(axis="x", length=0,which="both", direction="in")
ax.tick_params(axis="y", which="both", direction="in")
# （可选保险）如果你想把“边框线”也统一加粗/更清晰，可保留默认或自己调：
# for spine in ax.spines.values():
#     spine.set_linewidth(0.8)

# 数值标注
for i, row in enumerate(df.itertuples(index=False)):
    ax.text(
        x_pos[i],
        row.steps_int + max(y_max * 0.03, 0.2),
        f"{row.steps_int}",
        ha="center",
        va="bottom",
        fontsize=7,
        color="black"
    )

# 图例
legend_elements = [
    Patch(facecolor="white", edgecolor="black", hatch="//////", label="低复杂度（步骤 ≤ 3）"),
    Patch(facecolor="white", edgecolor="black", hatch="\\\\\\\\\\", label="中复杂度（3 < 步骤 ≤ 6）"),
    Patch(facecolor="white", edgecolor="black", hatch="xxxxx", label="高复杂度（步骤 > 6）"),
]
ax.legend(
    handles=legend_elements,
    loc="upper left",
    frameon=True,
    edgecolor="black"
)

# ======================
# 保存：PNG + SVG
# ======================
plt.tight_layout()

out_png = "intent_steps_bar_bw_unified.png"
out_svg = "intent_steps_bar_bw_unified.svg"
plt.savefig(out_png, dpi=300, bbox_inches="tight")
plt.savefig(out_svg, format="svg", bbox_inches="tight")
plt.close()

print(f"✅ 图表已保存至: {out_png}")
print(f"✅ 图表已保存至: {out_svg}")