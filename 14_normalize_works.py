#!/usr/bin/env python3
"""引用を「著作」の単位に名寄せする。

まとめ方をタイトルだけに頼ると、2方向に間違える。

  誤結合 — 『親族法』は泉久雄・我妻栄・穂積重遠・岡村司らが別々に書いている。
           タイトルが同じというだけで1件にまとめると、別の本が混ざる。
  分断   — 同じ本が『日本国憲法論[第2版]』『日本国憲法論(第2版)』のように
           括弧の種類だけ違って別件になる。著者名も 我妻榮/我妻栄、
           前掲長谷部恭男編/長谷部恭男編、地亨編（切れたもの）のように揺れる。

そこで「正規化したタイトル＋正規化した著者」で1つの著作とみなす。
著者の切れ・前掲つきは、同じタイトルの中で「長い名前の末尾に一致するか」で束ねる。
"""
import json, os, re, collections, csv, itertools, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
CV = "執筆者の業績（引用ではない）"
raw = json.load(open(os.path.join(HERE, "out_citations_raw.json")))

# 旧字体・異体字。法律文献は旧字のまま引かれることが多い
OLD2NEW = str.maketrans({
    "榮": "栄", "國": "国", "學": "学", "邊": "辺", "邉": "辺", "眞": "真", "澤": "沢",
    "廣": "広", "條": "条", "齋": "斎", "齊": "斉", "髙": "高", "濱": "浜", "瀨": "瀬",
    "淺": "浅", "縣": "県", "寶": "宝", "惠": "恵", "德": "徳", "應": "応", "樂": "楽",
    "靜": "静", "獨": "独", "舊": "旧", "萬": "万", "豐": "豊", "曉": "暁", "嶋": "島",
    "註": "注", "辯": "弁", "圓": "円", "處": "処", "數": "数", "體": "体", "會": "会",
    "關": "関", "藝": "芸", "假": "仮", "拂": "払", "從": "従", "增": "増", "單": "単",
    "臺": "台", "灣": "湾", "營": "営", "驗": "験", "櫻": "桜", "淵": "渕",
})
BRACKETS = "「」『』〔〕［］[]（）()【】〈〉《》"
REF_PREFIX = re.compile(r"^(?:前掲|前揭|後掲|同|参照|See|see|cf\.?)\s*")
# 表示に出すときに邪魔な、著者名の手前に紛れ込む語
DISPLAY_NOISE = re.compile(
    r"^(?:前掲|前揭|後掲|例えば|なお|参照|また|さらに|頁や|所収|その他|上記|下記|"
    r"については|同|は|の|や|・)+")


def norm_title(t):
    """版表記の括弧の違いなどを吸収する。中の文字は消さない（別の版は別の本なので）。"""
    t = unicodedata.normalize("NFKC", t).translate(OLD2NEW)
    t = re.sub(r"\s+", "", t)
    t = "".join(c for c in t if c not in BRACKETS)
    return t


def norm_author(a):
    a = unicodedata.normalize("NFKC", a or "").translate(OLD2NEW)
    a = re.sub(r"\s+", "", a)
    a = REF_PREFIX.sub("", a)
    a = a.strip("・=＝,、.")
    return a


rows = [r for r in raw if r["kind"] != CV]
cvs = [r for r in raw if r["kind"] == CV]
for r in rows:
    r["tn"] = norm_title(r["title"])
    r["an"] = norm_author(r["author"])

# ── 同じタイトルの中で、著者名の揺れを束ねる ──
#    「地亨編」は「青山道夫・有地亨編」の末尾に一致する＝同じ人の切れた表記とみなす
canon_map = {}
for tn, g in itertools.groupby(sorted(rows, key=lambda r: r["tn"]), key=lambda r: r["tn"]):
    g = list(g)
    names = collections.Counter(r["an"] for r in g if r["an"])
    longest = sorted(names, key=lambda x: (-len(x), -names[x]))
    canon = {}
    for n in longest:
        hit = next((c for c in canon.values()
                    if c.endswith(n) or n.endswith(c) or c in n or n in c), None)
        canon[n] = hit or n
    # 著者欄が空のものは、そのタイトルの著者が1人に定まるときだけ補う
    uniq = set(canon.values())
    fill = next(iter(uniq)) if len(uniq) == 1 else ""
    for r in g:
        canon_map[id(r)] = canon.get(r["an"], r["an"]) if r["an"] else fill

for r in rows:
    r["ac"] = canon_map[id(r)]

# ── 著作の単位にまとめ直す ──
works = collections.defaultdict(list)
for r in rows:
    works[(r["tn"], r["ac"])].append(r)

out = []
def display_author(g, ac):
    """表示用の著者名。「前掲◯◯」のような接頭辞が付かない綴りを優先する。"""
    cands = []
    for r in g:
        a = DISPLAY_NOISE.sub("", (r["author"] or "").strip())
        if a:
            cands.append(a)
    if not cands:
        return DISPLAY_NOISE.sub("", ac)
    return max(cands, key=len)


for (tn, ac), g in works.items():
    best = max(g, key=lambda r: len(r["source"]))
    cases = sorted({r["case"] for r in g})
    out.append({
        "title": best["title"], "author": display_author(g, ac), "author_norm": ac,
        "bracket": best.get("bracket", ""), "source": best["source"],
        "kind": collections.Counter(r["kind"] for r in g).most_common(1)[0][0],
        "出現回数": len(g), "出現ケース": cases, "ケース数": len(cases),
        "出現資料数": len({r["doc"] for r in g}),
        "case_title": best["case_title"], "doc_name": best["doc_name"],
        "pdf": best.get("pdf", ""), "case": best["case"], "context": best["context"],
        "表記ゆれ": sorted({r["title"] for r in g}) if len({r["title"] for r in g}) > 1 else [],
    })
out.sort(key=lambda r: (-r["ケース数"], -r["出現回数"], r["title"]))
json.dump(out, open(os.path.join(HERE, "out_works.json"), "w"), ensure_ascii=False, indent=1)

cross = [r for r in out if r["ケース数"] > 1]
json.dump(cross, open(os.path.join(HERE, "out_横断文献.json"), "w"), ensure_ascii=False, indent=1)

cases_all = {c["id"]: c["title"] for c in
             json.load(open(os.path.join(HERE, "cache", "cases_list.json")))["cases"]}
with open(os.path.join(HERE, "out_複数ケースで引用された文献.csv"), "w",
          encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ケース数", "引用回数", "種類", "著者", "タイトル", "出典",
                "引用したケース", "表記ゆれ"])
    for r in cross:
        w.writerow([r["ケース数"], r["出現回数"], r["kind"], r["author"], r["title"],
                    r["source"],
                    " / ".join(cases_all.get(c, c) for c in r["出現ケース"]),
                    " / ".join(r["表記ゆれ"])])

old = json.load(open(os.path.join(HERE, "out_citations.json")))
old_cross = [r for r in old if r["kind"] != CV and len(r["出現ケース"]) > 1]
print(f"生の検出 {len(rows):,}件（業績リスト{len(cvs)}件を除く）")
print(f"名寄せ前（タイトルだけでまとめた） 著作 {len({r['title'][:30] for r in rows}):,}件 / "
      f"複数ケース {len(old_cross)}件")
print(f"名寄せ後（タイトル＋著者）         著作 {len(out):,}件 / 複数ケース {len(cross)}件")
print()
print("=== 複数ケースで引用された文献 上位25 ===")
for r in cross[:25]:
    b = ("「", "」") if r["bracket"] == "「" else ("『", "』")
    a = f"{r['author']} " if r["author"] else ""
    print(f"  {r['ケース数']}ケース {r['出現回数']:>3}回  {a}{b[0]}{r['title'][:38]}{b[1]}")
