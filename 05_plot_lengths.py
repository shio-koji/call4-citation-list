#!/usr/bin/env python3
"""本文の文字数分布をヒストグラムにする。
狙いは「ドキュメント記載の50,000文字の上限が実際には掛かっていないこと」を目で見て分かるようにすること。
"""
import json, os, glob
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
plt.rcParams["font.family"] = "Hiragino Sans"
plt.rcParams["axes.unicode_minus"] = False

lengths = []
for f in glob.glob(os.path.join(HERE, "cache/text/*.json")):
    n = len(json.load(open(f)).get("text") or "")
    if n > 0:
        lengths.append(n)
lengths = np.array(sorted(lengths))
print(f"本文が取れた資料 {len(lengths)}件 / 最小 {lengths[0]:,} / 中央 {int(np.median(lengths)):,} / 最大 {lengths[-1]:,}")
json.dump([int(x) for x in lengths], open(os.path.join(HERE, "out_文字数.json"), "w"))

THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", ink3="#8a8981",
                  bar="#2a78d6", grid="#e7e6e2"),
    "dark":  dict(surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7", ink3="#8a8981",
                  bar="#3987e5", grid="#333330"),
}

CAP = 60000
BIN = 2000
for mode, C in THEMES.items():
    fig, ax = plt.subplots(figsize=(9.5, 4.6), dpi=200)
    fig.patch.set_facecolor(C["surface"])
    ax.set_facecolor(C["surface"])

    sub = lengths[lengths <= CAP]
    ax.hist(sub, bins=np.arange(0, CAP + BIN, BIN),
            color=C["bar"], edgecolor=C["surface"], linewidth=1.2)
    ax.axvline(50000, color=C["ink2"], linewidth=2, linestyle=(0, (5, 3)), zorder=5)
    ax.text(50000, ax.get_ylim()[1] * 1.02, "50,000文字", color=C["ink"],
            fontsize=10.5, ha="center", va="bottom")

    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(C["grid"]); ax.spines[s].set_linewidth(1)
    ax.tick_params(colors=C["ink2"], labelsize=9, length=3, width=1)
    ax.grid(axis="y", color=C["grid"], linewidth=1, alpha=0.9)
    ax.set_axisbelow(True)
    ax.set_xlabel("本文の文字数", color=C["ink2"], fontsize=10)
    ax.set_ylabel("資料の件数", color=C["ink2"], fontsize=10)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{int(v):,}"))

    n_over = int((lengths > CAP).sum())
    fig.suptitle(f"訴訟資料の本文の長さ（サンプル{len(lengths)}件・{BIN}文字ごと）",
                 color=C["ink"], fontsize=14.5, x=0.055, ha="left", y=0.955)
    fig.text(0.97, 0.035,
             f"※横軸は60,000文字まで。これを超える資料がさらに{n_over}件ある",
             color=C["ink3"], fontsize=9, ha="right")
    fig.subplots_adjust(top=0.835, bottom=0.175, left=0.085, right=0.97)

    out = os.path.join(HERE, f"fig_本文の長さ_{mode}.png")
    fig.savefig(out, facecolor=C["surface"])
    plt.close(fig)
    print("書き出し:", os.path.basename(out))
