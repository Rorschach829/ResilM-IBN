# 意图执行成功率与执行时间双轴图（黑白打印版）⭐️
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import os
import matplotlib
import matplotlib.font_manager as fm

font_path = "/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf"
prop = fm.FontProperties(fname=font_path)

# 用路径注册这款字体
fm.fontManager.addfont(font_path)

matplotlib.rcParams['font.family'] = prop.get_name()
matplotlib.rcParams['font.sans-serif'] = [prop.get_name()]
matplotlib.rcParams['axes.unicode_minus'] = False

print(f"✅ 已加载字体：{prop.get_name()} ({font_path})")
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

# ======== 第三步：根据 hosts 列分配填充样式 ========
def get_hatch(hosts):
    if hosts < 4:
        return "//"     # 小拓扑
    elif hosts < 10:
        return "\\"     # 中拓扑
    else:
        return "xx"     # 大拓扑

df["hatch"] = df["hosts"].apply(get_hatch)

# ======== 第四步：绘图并保存 ========
fig, ax1 = plt.subplots(figsize=(14, 6))

# 左轴：平均耗时柱状图（不同填充样式）
bars = []
for _, row in df.iterrows():
    bar = ax1.bar(
        row["intent_id"],
        row["avg_time"],
        color="white",
        edgecolor="black",
        hatch=row["hatch"],
        linewidth=1.0
    )
    bars.append(bar)

ax1.set_xlabel("意图编号", fontsize=12)
ax1.set_ylabel("平均执行时间 (秒)", fontsize=12)
ax1.tick_params(axis="y", labelsize=10)
ax1.set_ylim(0, df["avg_time"].max() * 1.2)
ax1.grid(axis="y", linestyle="--", alpha=0.6)

# 在柱子上标注数值
for bar_group in bars:
    bar = bar_group[0]
    height = bar.get_height()
    ax1.text(
        bar.get_x() + bar.get_width() / 2,
        height + 0.3,
        f"{height:.1f}",
        ha="center",
        va="bottom",
        fontsize=9,
        color="black"
    )

# 右轴：成功率折线图（实线+标记）
ax2 = ax1.twinx()
ax2.plot(
    df["intent_id"],
    df["success_rate"],
    color="black",
    marker="o",
    linestyle="-",
    linewidth=1.5,
    markersize=6
)
ax2.set_ylabel("执行成功率 (%)", fontsize=12)
ax2.tick_params(axis="y", labelsize=10)
ax2.set_ylim(0, 110)

# X 轴标签
plt.xticks(ticks=df["intent_id"], labels=df["intent_id"], fontsize=10)

# 图例（使用不同填充样式区分拓扑规模）
legend_elements = [
    Patch(facecolor='white', edgecolor='black', hatch='//', label='小型拓扑 (主机数 < 4)'),
    Patch(facecolor='white', edgecolor='black', hatch='\\', label='中型拓扑 (4 ≤ 主机数 < 10)'),
    Patch(facecolor='white', edgecolor='black', hatch='xx', label='大型拓扑 (主机数 ≥ 10)'),
    Patch(facecolor='white', edgecolor='black', label='平均执行时间（柱）'),
    Line2D([0], [0], color='black', marker='o', linestyle='-', linewidth=1.5, markersize=5, label='执行成功率（线）')
]
plt.legend(
    handles=legend_elements,
    loc="upper left",
    bbox_to_anchor=(1.16, 1.0),
    fontsize=10
)

# 图标题
plt.title("不同拓扑规模下的意图执行时间与成功率", fontsize=14)

# 布局与保存
plt.tight_layout(rect=[0, 0, 0.82, 1])
output_path = os.path.join(latest_dir, "intent_time_success_bw.png")
plt.savefig(output_path, dpi=300, bbox_inches="tight")
print(f"✅ 图表已保存至: {output_path}")