#!/usr/bin/env python3
"""複数ケースで引用された文献の調査結果を中間報告にする。"""
import json, os, collections, itertools

HERE = os.path.dirname(os.path.abspath(__file__))
cross = json.load(open(os.path.join(HERE, "out_横断文献.json")))
works = json.load(open(os.path.join(HERE, "out_works.json")))
raw = json.load(open(os.path.join(HERE, "out_citations_raw.json")))
cases = {c["id"]: c for c in
         json.load(open(os.path.join(HERE, "cache", "cases_list.json")))["cases"]}
tag = lambda c: {t for t in cases[c].get("tags", []) if t != "アーカイブ"}
CV = "執筆者の業績（引用ではない）"

fmt = lambda r: (f"{r['author']} " if r["author"] else "") + \
    (f"「{r['title']}」" if r["bracket"] == "「" else
     f"『{r['title']}』" if r["bracket"] else r["title"])

pair = collections.Counter()
for r in cross:
    for a, b in itertools.combinations(sorted(r["出現ケース"]), 2):
        pair[(a, b)] += 1
truly = [r for r in cross
         if any(not (tag(a) & tag(b))
                for a, b in itertools.combinations(r["出現ケース"], 2))]
cc = collections.Counter()
for r in cross:
    for c in r["出現ケース"]:
        cc[c] += 1
dist = collections.Counter(r["ケース数"] for r in cross)
old = json.load(open(os.path.join(HERE, "out_citations.json")))
old_cross = len([r for r in old if r["kind"] != CV and len(r["出現ケース"]) > 1])

L = []; a = L.append
a("# 中間報告⑤ 複数ケースで引用されている文献を全部調べた\n")
a("「分野を越えて引用されている文献」を全件精査しました。"
  "**結論から言うと、最初に出した162件という数字は作り方が甘く、"
  "『分野を越えて』という言い方も半分は不正確でした。** 両方を直した結果を書きます。\n")
a("---\n")
a("## まず、まとめ方が間違っていた\n")
a("前回はタイトルだけで「同じ文献」と判定していました。これは2方向に間違えます。\n")
a("### 誤って1つにまとめてしまう（同名異書）\n")
a("`『親族法』` を引用している箇所を著者別に数えると、こうなっていました。\n")
byt = collections.defaultdict(collections.Counter)
for r in raw:
    if r["kind"] != CV:
        byt[r["title"][:30]][r["author"] or "(著者欄なし)"] += 1
a("| 著者 | 引用回数 |")
a("|---|---:|")
for au, n in byt["親族法"].most_common(7):
    a(f"| {au} | {n} |")
a("")
a("**泉久雄・我妻栄・穂積重遠・岡村司・野上久幸・中川善之助は、それぞれ別の本を書いています。**"
  "これを1件として「4ケースで引用」と数えていました。\n")
a("### 誤って別々にしてしまう（表記ゆれ）\n")
a("逆に、同じ本が別件として数えられていました。\n")
a("| 揺れの種類 | 例 |")
a("|---|---|")
a("| 括弧の違い | `日本国憲法論[第2版]` と `日本国憲法論(第2版)` |")
a("| 旧字体 | `我妻榮` と `我妻栄`、`註解` と `注解` |")
a("| 「前掲」の混入 | `前掲長谷部恭男編` と `長谷部恭男編` |")
a("| 名前の切れ | `地亨編`（`青山道夫・有地亨編` の末尾）、`恭男編`、`平編` |")
a("")
a("### 直し方\n")
a("**「正規化したタイトル＋正規化した著者」を1つの著作**とみなすようにしました（`14_normalize_works.py`）。\n")
a("- タイトル: 全角半角を揃え、括弧記号を除去（**版数の数字は残す**。第7版と第8版は別の本なので）")
a("- 著者: 全角半角を揃え、旧字体を新字体に直し、`前掲`などの接頭辞を除去")
a("- 名前の切れ: 同じタイトルの中で「長い名前の末尾に一致する」ものを同一人物として束ねる")
a("- 著者欄が空の引用: そのタイトルの著者が1人に定まるときだけ補う\n")
a(f"結果、**{old_cross}件 → {len(cross)}件**になりました。"
  "数は増えていますが、これは誤結合をほどいた分が、表記ゆれの統合より多かったためです。\n")
a("---\n")
a("## 調査結果\n")
a(f"複数のケースで引用されている文献は **{len(cross)}件**です"
  f"（全著作 {len(works):,}件のうち {len(cross)/len(works):.1%}）。\n")
a("| ケース数 | 文献数 |")
a("|---:|---:|")
for n in sorted(dist, reverse=True):
    a(f"| {n}ケース | {dist[n]}件 |")
a("")
a("| 種類 | 件数 |")
a("|---|---:|")
for k, n in collections.Counter(r["kind"] for r in cross).most_common():
    a(f"| {k} | {n}件 |")
a("")
a("**書籍が圧倒的**です。訴訟で繰り返し参照されるのは、個別の論文より"
  "体系書・注釈書（コンメンタール）だということになります。\n")
a("### 最上位\n")
a("| ケース数 | 回数 | 文献 |")
a("|---:|---:|---|")
for r in cross[:20]:
    a(f"| {r['ケース数']} | {r['出現回数']} | {fmt(r)[:60]} |")
a("")
a("---\n")
a("## 「分野を越えて」は半分しか正しくなかった\n")
a("前回サイトに『分野を越えて引用されている文献』と書きましたが、"
  "**共有の大半は同じ主題のケース同士**でした。\n")
a("| 共有文献数 | 関係 | ケースの組 |")
a("|---:|---|---|")
for (x, y), n in pair.most_common(8):
    rel = "同じ主題" if tag(x) & tag(y) else "**主題が異なる**"
    a(f"| {n} | {rel} | {cases[x]['title'][:26]} ／ {cases[y]['title'][:26]} |")
a("")
a("上位は同性婚関連の訴訟同士です。同じ争点を争っているのだから文献が重なるのは当然で、"
  "これを「分野を越えた」と呼ぶのは言い過ぎでした。\n")
a("### 本当に分野を越えているもの\n")
a(f"主題タグが**まったく重ならない**ケース同士で引用されている文献に絞ると、**{len(truly)}件**です。\n")
a("| ケース数 | 文献 | またいだ分野 |")
a("|---:|---|---|")
for r in sorted(truly, key=lambda r: (-r["ケース数"], -r["出現回数"]))[:15]:
    tg = sorted({t for c in r["出現ケース"] for t in tag(c)})
    a(f"| {r['ケース数']} | {fmt(r)[:44]} | {'・'.join(tg)[:54]} |")
a("")
a("**ほぼ全部が憲法の体系書・注釈書です。** 長谷部恭男編『註釈日本国憲法』、"
  "佐藤幸治『日本国憲法論』、渋谷秀樹『憲法』、高橋和之『立憲主義と日本国憲法』、"
  "芦部信喜『憲法』。行政法では宇賀克也『行政法概説』。\n")
a("これは考えてみれば当然の結果で、**公共訴訟はほぼ必ず憲法問題を含む**ため、"
  "分野が違っても同じ憲法の教科書に行き着きます。"
  "逆に言えば、**この数十冊が日本の公共訴訟の共通言語になっている**ということです。\n")
a("---\n")
a("## どのケースが文献を共有しているか\n")
a(f"横断文献を1件でも持つケースは **{len(cc)}件 / 96件**でした。\n")
a("| 共有文献数 | ケース | 主題 |")
a("|---:|---|---|")
for c, n in cc.most_common(12):
    a(f"| {n} | [{cases[c]['title'][:34]}](https://www.call4.jp/info.php?type=items&id={c}) "
      f"| {'・'.join(sorted(tag(c)))[:30]} |")
a("")
a("**同性婚関連の3訴訟が突出**しています（83・77・63件）。"
  "同じ論点を別の裁判所で争っているため、文献の基盤を共有しているわけです。"
  "残り半分のケース（53件）は横断文献を持ちません。"
  "証拠中心の訴訟や、資料が少ない訴訟が該当します。\n")
a("---\n")
a("## 出版社\n")
a("横断文献の出版元を数えました。\n")
PUB = ["有斐閣", "日本評論社", "岩波", "信山社", "三省堂", "弘文堂", "法律文化社",
       "日本加除出版", "新世社", "勁草", "成文堂", "青林書院", "東京大学出版会"]
pc = collections.Counter()
for r in cross:
    for p in PUB:
        if p in r["source"] or p in r.get("context", ""):
            pc[p] += 1
            break
a("| 出版社 | 件数 |")
a("|---|---:|")
for p, n in pc.most_common(8):
    a(f"| {p} | {n} |")
a("")
a(f"**有斐閣だけで{pc.get('有斐閣', 0)}件**と、突出しています。法学の体系書の主要な出し手が"
  "そのまま公共訴訟の土台になっていることが数字で見えます。\n")
a("---\n")
a("## この調査の限界\n")
a("- **名寄せは機械的**です。同じ本の版違い（`憲法(第7版)` と `憲法〔第8版〕`）は"
  "別の著作として数えています。内容が違うので分けるのが正しいと判断しましたが、"
  "「同じ著作の系譜」として見たい場合は別の集計が要ります")
a("- **著者欄が取れていない文献が残っています。** `『憲法I基本権〔第2版〕』` のように、"
  "同じタイトルに複数の著者表記が現れて1人に定まらなかったものは著者空欄のままです")
a("- **省略引用（`前掲注(24)`）は依然として拾えていません。** "
  "実際の引用回数はここに出ている数より多いはずです")
a("- **人手による正誤確認はしていません。** 精度の数値は出していません\n")
a("---\n")
a("## データの置き場所\n")
a("| ファイル | 中身 |")
a("|---|---|")
a(f"| `out_複数ケースで引用された文献.csv` | **{len(cross)}件の全件**（引用したケース名・表記ゆれつき） |")
a("| `out_横断文献.json` | 同上（生データ） |")
a(f"| `out_works.json` | 名寄せ後の全著作 {len(works):,}件 |")
a("| `out_citations_raw.json` | まとめる前の1件ずつの検出結果 |")
a("| `14_normalize_works.py` | 名寄せのスクリプト |")

open(os.path.join(HERE, "中間報告05_複数ケースで引用されている文献.md"), "w").write("\n".join(L))
print("\n".join(L[:22]))
