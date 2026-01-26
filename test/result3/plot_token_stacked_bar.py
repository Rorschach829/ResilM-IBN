#意图token消耗均值图
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.ticker import FuncFormatter   # ✅ 新增：纵轴千分空格格式

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
    "font.size": 6.5,
    "axes.titlesize": 6.5,
    "axes.labelsize": 6.5,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "legend.fontsize": 6,
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

# ✅ 纵轴：4位数以上加千分空格（0~999 原样）
def y_thousands_space(x, pos):
    # token 是计数，这里按整数显示更自然；如果你想保留小数我也能给你一版
    xi = int(round(x))
    if abs(xi) >= 1000:
        return f"{xi:,}".replace(",", " ")
    return str(xi)

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

    ax.text(
        i, top + max(total_mean) * 0.002,
        text,
        ha="center", va="bottom",
        fontsize=7.5
    )

ax.set_title("各意图平均Token消耗（柱顶标注波动）")
ax.set_xlabel("意图编号")
ax.set_ylabel("Token消耗数量 /个")

ax.set_xticks(x)
ax.set_xticklabels(df["intent_id"].astype(str).tolist())

# ✅ 要求1：纵坐标轴短线在里面
ax.tick_params(axis="y", which="both", direction="in")

# ✅ 要求2：横轴去掉短线（保留标签）
ax.tick_params(axis="x", which="both", length=0)

# ✅ 要求3：纵轴4位数以上加千分空格
ax.yaxis.set_major_formatter(FuncFormatter(y_thousands_space))

# ax.legend(frameon=True)
ax.legend(
    loc="upper left",
    # bbox_to_anchor=(1.02, 1.0),
    ncol=1,
    frameon=True
)
ax.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.6)

fig.tight_layout()

# ✅ 原有输出 PNG
fig.savefig("fig_token_stacked_bar_bw_with_std_text.png", bbox_inches="tight")

# ✅ 要求4：额外输出 SVG
fig.savefig("fig_token_stacked_bar_bw_with_std_text.svg", format="svg", bbox_inches="tight")

plt.close(fig)

print("[OK] 已生成 fig_token_stacked_bar_bw_with_std_text.png / svg")
print("[INFO] 若想标注 CV%，请将 USE_CV=True")