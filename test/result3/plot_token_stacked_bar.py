#意图token消耗均值图
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ======== 字体设置（使用服务器指定字体路径） ========
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

df["intent_mean"] = intent_runs.apply(np.mean)
df["json_mean"]   = json_runs.apply(np.mean)

df["total_runs"] = [a + b for a, b in zip(intent_runs, json_runs)]
df["total_mean"] = df["total_runs"].apply(np.mean)
df["total_std"]  = df["total_runs"].apply(np.std)

# 你可以在这里切换标注内容：
USE_CV = False  # True -> 标注CV%，False -> 标注±std

df = df.sort_values("intent_id").reset_index(drop=True)

x = np.arange(len(df))
intent_mean = df["intent_mean"].to_numpy()
json_mean   = df["json_mean"].to_numpy()
total_mean  = df["total_mean"].to_numpy()
total_std   = df["total_std"].to_numpy()

fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=300)

ax.bar(
    x, intent_mean,
    label="意图解析Agent消耗Token（均值）",
    color="white", edgecolor="black",
    hatch="///", linewidth=0.8
)
ax.bar(
    x, json_mean,
    bottom=intent_mean,
    label="JSON生成Agent消耗Token（均值）",
    color="white", edgecolor="black",
    hatch="\\\\\\", linewidth=0.8
)

# ======== 柱顶标注：±std 或 CV% ========
for i in range(len(df)):
    top = intent_mean[i] + json_mean[i]
    if USE_CV:
        cv = (total_std[i] / total_mean[i] * 100.0) if total_mean[i] > 0 else 0.0
        text = f"CV={cv:.2f}%"
    else:
        text = f"±{total_std[i]:.1f}"

    # 在柱顶稍微上移一点点
    ax.text(
        i, top + max(total_mean) * 0.002,
        text,
        ha="center", va="bottom",
        fontsize=7.5
    )

ax.set_title("各意图平均Token消耗（柱顶标注波动）")
ax.set_xlabel("意图编号")
ax.set_ylabel("Token数")

ax.set_xticks(x)
ax.set_xticklabels(df["intent_id"].astype(str).tolist())

# ax.legend(frameon=True)
ax.legend(
    loc="upper left",
    bbox_to_anchor=(1.02, 1.0),
    ncol=1,
    frameon=False
)
ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6)

fig.tight_layout()
# fig.savefig("fig_token_stacked_bar_bw_with_std_text.pdf", bbox_inches="tight")
fig.savefig("fig_token_stacked_bar_bw_with_std_text.png", bbox_inches="tight")
plt.close(fig)

print("[OK] 已生成 fig_token_stacked_bar_bw_with_std_text.pdf / png")
print("[INFO] 若想标注 CV%，请将 USE_CV=True")