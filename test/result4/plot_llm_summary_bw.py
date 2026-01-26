import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch

# ======================
# Font settings (exactly as requested)
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
    "font.size": 7.5,
    "axes.titlesize": 7.5,
    "axes.labelsize": 7.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
})

# ======================
# Config
# ======================
CSV_FILE = "llm_summary.csv"
OUT_PNG = "llm_perf_dual_bar_bw_cn.png"
OUT_SVG = "llm_perf_dual_bar_bw_cn.svg"  # ✅ 新增 SVG

MODEL_ORDER = [
    "GLM-4.6",
    "kimi-k2-think",
    "GLM4.6-think",
    "Qwen-plus",
    "deepseek-chat"
]

MODEL_ALIAS = {
    "GLM4.6-nothink": "GLM-4.6",
    "GLM4.6-nothinking": "GLM-4.6",
    "GLM-4.6-nothink": "GLM-4.6",
    "GLM4.6-no_thinking": "GLM-4.6",

    "GLM4.6-think": "GLM4.6-think",
    "GLM-4.6-think": "GLM4.6-think",

    "kimi-k2-think": "kimi-k2-think",
    "kimi2": "kimi-k2-think",

    "Qwen-plus": "Qwen-plus",
    "qwen-plus": "Qwen-plus",

    "deepseek-chat": "deepseek-chat",
    "ds_chat": "deepseek-chat",
}

def main():
    if not os.path.exists(CSV_FILE):
        raise FileNotFoundError(f"找不到 {CSV_FILE}，当前目录：{os.getcwd()}")

    df = pd.read_csv(CSV_FILE)

    required = ["model", "success_rate", "avg_time"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"{CSV_FILE} 缺少列 {c}，实际列：{list(df.columns)}")

    df["model"] = df["model"].astype(str).str.strip()
    df["model_norm"] = df["model"].map(MODEL_ALIAS).fillna(df["model"])

    df["success_rate"] = pd.to_numeric(df["success_rate"], errors="coerce")
    df["avg_time"] = pd.to_numeric(df["avg_time"], errors="coerce")
    df = df.dropna(subset=["success_rate", "avg_time"]).copy()

    keep = df[df["model_norm"].isin(MODEL_ORDER)].copy()
    missing = [m for m in MODEL_ORDER if m not in set(keep["model_norm"])]
    if missing:
        print("⚠️ 警告：下列模型在 llm_summary.csv 中未找到，将被跳过：", missing)

    keep["model_norm"] = pd.Categorical(keep["model_norm"], categories=MODEL_ORDER, ordered=True)
    keep = keep.sort_values("model_norm")

    models = keep["model_norm"].astype(str).tolist()
    success_pct = (keep["success_rate"] * 100.0).tolist()
    avg_time = keep["avg_time"].tolist()

    x = list(range(len(models)))

    # ======================
    # Plot
    # ======================
    fig, ax1 = plt.subplots(figsize=(6.8, 2.9), dpi=300)

    width = 0.36
    offset = 0.20
    x_left = [i - offset for i in x]
    x_right = [i + offset for i in x]

    bars1 = ax1.bar(
        x_left, success_pct,
        width=width,
        facecolor="white",
        edgecolor="black",
        linewidth=1.0,
        hatch="///",
        label="平均执行成功率"
    )
    ax1.set_ylabel("平均执行成功率")
    ax1.set_ylim(0, 119)
    from matplotlib.ticker import FuncFormatter

    def percent_formatter(x, pos):
        if abs(x) < 1e-9:   # 处理 0 或浮点误差
            return "0"
        return f"{int(x)}%"

    ax1.yaxis.set_major_formatter(FuncFormatter(percent_formatter))

    # ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{int(x)}%"))
    ax2 = ax1.twinx()
    bars2 = ax2.bar(
        x_right, avg_time,
        width=width,
        facecolor="white",
        edgecolor="black",
        linewidth=1.0,
        hatch="...",
        label="平均执行时长 /s"
    )
    ax2.set_ylabel("平均执行时长 /s")

    ax1.set_xticks(x)
    ax1.set_xticklabels(models, rotation=0, ha="center")

    # ✅ 要求1：纵轴短线朝内（左 y & 右 y）
    ax1.tick_params(axis="y", which="both", direction="in")
    ax2.tick_params(axis="y", which="both", direction="in")

    # ✅ 要求2：横轴短线去掉（只去掉 x 轴短线，不动标签）
    ax1.tick_params(axis="x", which="both", length=0)

    ax1.grid(True, axis="y", linestyle="--", linewidth=0.6, color="black", alpha=0.20)
    ax1.set_title("不同大语言模型下的平均执行成功率与执行时长对比")

    def annotate(ax, bars, fmt_func):
        for b in bars:
            h = b.get_height()
            ax.annotate(
                fmt_func(h),
                xy=(b.get_x() + b.get_width() / 2, h),
                xytext=(0, 2),
                textcoords="offset points",
                ha="center",
                va="bottom"
            )

    annotate(ax1, bars1, lambda v: f"{v:.1f}%")
    annotate(ax2, bars2, lambda v: f"{v:.1f}")

    legend_handles = [
        Patch(facecolor="white", edgecolor="black", hatch="///", label="平均执行成功率"),
        Patch(facecolor="white", edgecolor="black", hatch="...", label="平均执行时长"),
    ]

    # ✅ 要求3：图例放在框图内左上角
    ax1.legend(
        handles=legend_handles,
        loc="upper right",
        ncol=2,
        frameon=True,
        edgecolor="black"
    )

    fig.tight_layout()

    # ✅ 要求4：分别保存 PNG 和 SVG
    fig.savefig(OUT_PNG, bbox_inches="tight")
    fig.savefig(OUT_SVG, format="svg", bbox_inches="tight")

    print(f"✅ 已生成图像：{OUT_PNG}")
    print(f"✅ 已生成图像：{OUT_SVG}")

if __name__ == "__main__":
    main()