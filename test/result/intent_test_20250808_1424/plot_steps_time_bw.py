#生成执行时间和意图拆解步骤数的散点图
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ======== 字体设置（使用服务器指定字体路径） ========
# ======== 中文字体（宋体） ========
cn_font_path = "/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf"
fm.fontManager.addfont(cn_font_path)
cn_prop = fm.FontProperties(fname=cn_font_path)

# ======== 英文字体（Times New Roman） ========
tnr_font_path = "/data/gjw/Times New Roman.ttf"
fm.fontManager.addfont(tnr_font_path)
tnr_prop = fm.FontProperties(fname=tnr_font_path)

# ======== 字体回退顺序 ========
# 中文字符优先用宋体，英文/数字自动回退到 Times New Roman
matplotlib.rcParams['font.family'] = [
    cn_prop.get_name(),
    tnr_prop.get_name()
]

# 负号正常显示
matplotlib.rcParams['axes.unicode_minus'] = False
# ======== 图中文字字号（正文 11 号，对应下调） ========
matplotlib.rcParams.update({
    "font.size": 9.5,        # 图内默认字号（整体 < 正文）
    "axes.titlesize": 10,    # 图标题
    "axes.labelsize": 9.5,   # 坐标轴标题
    "xtick.labelsize": 9,    # x 轴刻度
    "ytick.labelsize": 9,    # y 轴刻度
    "legend.fontsize": 9,    # 图例
})

# ======== 数据读取 ========
csv_path = "intent_data_processed.csv"
df = pd.read_csv(csv_path)

# 确保数值类型正确
df["steps"] = pd.to_numeric(df["steps"], errors="coerce")
df["avg_time"] = pd.to_numeric(df["avg_time"], errors="coerce")
df["hosts"] = pd.to_numeric(df["hosts"], errors="coerce")
df = df.dropna(subset=["steps", "avg_time", "hosts"])


# ======== 拓扑规模分类 ========
def topo_class(hosts):
    if hosts < 4:
        return "小型拓扑"
    elif hosts < 10:
        return "中型拓扑"
    else:
        return "大型拓扑"


df["topology"] = df["hosts"].apply(topo_class)

# ======== 形状映射（黑白） ========
marker_map = {
    "小型拓扑": "o",   # 圆形
    "中型拓扑": "s",   # 方形
    "大型拓扑": "^",   # 三角形
}

# ======== 绘图 ========
fig, ax = plt.subplots(figsize=(6.5, 4.2))

for topo, marker in marker_map.items():
    sub = df[df["topology"] == topo]
    if sub.empty:
        continue
    ax.scatter(
        sub["steps"],
        sub["avg_time"],
        marker=marker,
        s=55,
        facecolors="none",   # 空心点，黑白友好
        edgecolors="black",
        linewidths=1.1,
        label=topo
    )

# ======== 坐标轴与图例 ========
ax.set_xlabel("意图拆解步骤数")
ax.set_ylabel("平均执行时间（秒）")
ax.set_title("任务复杂度与意图执行时间关系")

# 横轴只显示实际出现过的 steps（离散）
step_ticks = sorted(df["steps"].astype(int).unique())
ax.set_xticks(step_ticks)

# 网格（淡灰虚线，不抢视觉）
ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.5)

# 图例（中文）
ax.legend(frameon=True)

plt.tight_layout()
plt.savefig("steps_vs_time_bw_scatter.png", dpi=300)
print("中文字体名:", cn_prop.get_name())
print("英文字体名:", tnr_prop.get_name())
