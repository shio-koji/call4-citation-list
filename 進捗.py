#!/usr/bin/env python3
"""いま何件まで取得できたかを表示する。取得中でも後からでも実行できる。
    python3 進捗.py          1回だけ表示
    python3 進捗.py -w       5秒ごとに更新し続ける（Ctrl+C で終了）
"""
import json, os, sys, time, glob

HERE = os.path.dirname(os.path.abspath(__file__))
TXT = os.path.join(HERE, "cache", "text")
STAMP = os.path.join(HERE, "cache", ".progress_start")

total = sum(len(json.load(open(f))["documents"])
            for f in glob.glob(os.path.join(HERE, "cache", "docs_*.json")))


def snapshot():
    files = os.listdir(TXT) if os.path.isdir(TXT) else []
    n = len(files)
    # 起点を覚えておいて、そこからの速度を出す
    if not os.path.exists(STAMP):
        json.dump({"t": time.time(), "n": n}, open(STAMP, "w"))
    s = json.load(open(STAMP))
    el = time.time() - s["t"]
    gained = n - s["n"]
    rate = gained / el * 60 if el > 30 and gained > 0 else 0
    eta = (total - n) / rate if rate else 0
    return n, rate, eta


def line():
    n, rate, eta = snapshot()
    pct = n / total * 100
    bar = "█" * int(pct / 2.5) + "·" * (40 - int(pct / 2.5))
    s = f"[{bar}] {n:,}/{total:,} ({pct:5.1f}%)"
    if rate:
        h, m = divmod(int(eta), 60)
        s += f"  {rate:.0f}件/分  残り約{h}時間{m:02d}分"
    else:
        s += "  （速度を測定中）"
    return s


if "-w" in sys.argv:
    try:
        while True:
            print("\r" + line(), end="", flush=True)
            if snapshot()[0] >= total:
                print("\n完了")
                break
            time.sleep(5)
    except KeyboardInterrupt:
        print()
else:
    print(line())
