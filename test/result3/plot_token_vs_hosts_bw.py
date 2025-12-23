import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ======== 字体设置（与你给的一致） ========
cn_font_path = "/usr/share/fonts/truetype/arphic-gbsn00lp/gbsn00lp.ttf"
fm.fontManager.addfont(cn_font_path)
cn_prop = fm.FontProperties(fname=cn_font_path)

tnr_font_path = "/data/gjw/Times New Roman.ttf"
fm.fontManager.addfont(tnr_font_path)
tnr_prop = fm.FontProperties(fname=tnr_font_path)

matplotlib.rcParams['font.family'] = [
    cn_prop.get_name(),
    tnr_prop.get_name()
]
matplotlib.rcParams['axes.unicode_minus'] = False

matplotlib.rcParams.update({
    "font.size": 9.5,
    "axes.titlesize": 10,
    "axes.labelsize": 9.5,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
})

# ======== 数据读取 ========
df = pd.read_csv("intent_token.csv")

def parse_runs(x, n=3):
    s = str(x).strip()
    if "+" in s:
        vals = [float(v.strip()) for v in s.split("+") if v.strip()]
        return np.array(vals, dtype=float)
    v = float(s)
    return np.array([v] * n, dtype=float)

intent_runs = df["intent_token"].apply(parse_runs)
json_runs   = df["json_token"].apply(parse_runs)

# 端到端总 token（按 3 次对应相加）
df["total_runs"] = [a + b for a, b in zip(intent_runs, json_runs)]
df["total_mean"] = df["total_runs"].apply(np.mean)

# ======== 按你论文规则分桶 ========
def topo_size(hosts: int) -> str:
    h = int(hosts)
    if h < 4:
        return "小型拓扑"
    elif 4 <= h < 10:
        return "中型拓扑"
    else:
        return "大型拓扑"

df["topo_size"] = df["hosts"].apply(topo_size)

# ======== 分组统计：跨意图的均值与标准差 ========
stat = df.groupby("topo_size")["total_mean"].agg(["mean", "std", "count"]).reset_index()

# 固定顺序（不然 pandas 可能按字典序排）
order = ["小型拓扑", "中型拓扑", "大型拓扑"]
stat["topo_size"] = pd.Categorical(stat["topo_size"], categories=order, ordered=True)
stat = stat.sort_values("topo_size")

labels = stat["topo_size"].tolist()
means  = stat["mean"].to_numpy()
stds   = stat["std"].fillna(0).to_numpy()
counts = stat["count"].to_numpy()

# ======== 画图：黑白柱状 + 误差棒 ========
fig, ax = plt.subplots(figsize=(5.6, 3.2), dpi=300)

x = np.arange(len(labels))
bars = ax.bar(
    x, means,
    color="white",
    edgecolor="black",
    hatch="///",
    linewidth=0.8,
    label="总 Token（均值）"
)

ax.errorbar(
    x, means, yerr=stds,
    fmt="none",
    ecolor="black",
    elinewidth=0.8,
    capsize=3,
)

ax.set_title("不同拓扑规模下的总 Token 消耗")
ax.set_xlabel("拓扑规模（按主机数量划分）")
ax.set_ylabel("总 Token 数（平均）")

ax.set_xticks(x)
ax.set_xticklabels(labels)

# 在柱子顶部标注样本量 n（建议加，防审稿人问）
for i, (m, n) in enumerate(zip(means, counts)):
    ax.text(i, m, f"n={int(n)}", ha="center", va="bottom", fontsize=9)

ax.legend(frameon=True)
ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6)

fig.tight_layout()
# fig.savefig("fig_total_token_by_topo_size_bw.pdf", bbox_inches="tight")
fig.savefig("fig_total_token_by_topo_size_bw.png", bbox_inches="tight")
plt.close(fig)

print("[OK] 已生成 fig_total_token_by_topo_size_bw.pdf / png")
print(stat.to_string(index=False))