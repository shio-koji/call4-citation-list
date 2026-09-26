#!/usr/bin/env python3
"""訴訟資料の本文から、引用されている学術文献（論文・書籍）を拾う。

考え方
  日本語の文献引用は「著者『書名』(出版社、年)頁」「著者「論文名」雑誌名号数頁」の形を取り、
  書誌情報はかならず **タイトルの直後** に続く。そこで鉤括弧の後ろ60文字だけを見て、
  出版社・発行年・頁・雑誌名が続くものだけを引用とみなす。
  本文中の強調や用語（「特定活動」など）は後ろに書誌情報が続かないので自然に落ちる。

  一方で「準備書面12頁」「民集59巻7号2087頁」「甲15・3頁」も同じ形をしているため、
  訴訟書面の自己参照・判例・証拠番号は明示的に除外する。

出力は候補であって確定ではない。人が見て捨てる前提で、やや過剰に拾う側に倒してある。
"""
import json, os, re, collections, csv

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = ["I0000090", "I0000111", "I0000120", "I0000159"]

JOURNALS = ["ジュリスト", "法律時報", "法学教室", "法学セミナー", "法曹時報", "曹時",
            "民商法雑誌", "法学協会雑誌", "国家学会雑誌", "法学論叢", "法学研究",
            "自治研究", "法律のひろば", "判例評論", "重要判例解説", "判例時報", "判例タイムズ", "法と政治", "法政論集", "論究ジュリスト",
            "季刊労働法", "日本労働研究雑誌", "社会保障法研究", "家族〈社会と法〉",
            "紀要", "論集", "論叢", "年報", "法政研究", "早稲田法学", "法社会学",
            "比較法研究", "公法研究", "憲法問題", "国際人権", "現代思想",
            "都市計画", "ランドスケープ研究", "造園雑誌", "建築雑誌", "学会誌"]
PUBLISHERS = ["書房", "出版", "書店", "有斐閣", "岩波", "日本評論社", "弘文堂",
              "成文堂", "法曹会", "信山社", "勁草", "ミネルヴァ", "東京大学出版会",
              "大学出版", "新曜社", "青弓社", "明石書店", "現代人文社", "商事法務",
              "新聞社", "講談社", "筑摩", "中央公論", "文藝春秋", "刊行会"]
CASE_REPORTERS = ["民集", "刑集", "集民", "集刑", "判時", "判タ", "判例時報",
                  "判例タイムズ", "裁時", "訟月", "行集", "下民集", "労判",
                  "判例地方自治", "家月"]
SELF_REF = ["準備書面", "訴状", "答弁書", "上告理由書", "控訴理由書", "原判決",
            "本判決", "第一審判決", "反論書", "求釈明", "証拠説明書", "陳述書",
            "上申書", "申立書", "補充書", "本書面", "前記第", "別紙", "本件"]

PAGE = re.compile(r"\d[\d,\s]{0,6}(?:頁|ページ)|pp?\.\s?\d")
YEAR = re.compile(r"(?:1[89]\d\d|20\d\d)\s?年|(?:平成|昭和|令和)\s?\d{1,2}\s?年")
VOLNUM = re.compile(r"\d+\s?号")
EN_CITE = re.compile(
    r"[A-Z][A-Za-z\.\,\'\-\s&:]{12,130}?"
    r"(?:Press|Journal|Review|University|Publishers?|Quarterly|Studies|Handbook)"
    r"[A-Za-z\.\,\'\-\s0-9\(\)]{0,90}")
norm = lambda s: re.sub(r"\s+", "", s or "")
HTML = re.compile(r"<[^>]{1,40}>")
# 意見書の末尾に付く執筆者の業績リスト。引用ではないので分けて扱う
CV_MARK = ["主要業績", "主な業績", "研究業績", "著書", "略歴", "経歴",
           "単著", "共著", "編著", "主要著作", "業績一覧"]


def excluded(ctx):
    if any(w in ctx for w in SELF_REF):
        return True
    if any(w in ctx for w in CASE_REPORTERS) and re.search(r"\d+\s?巻", ctx):
        return True
    if re.search(r"[甲乙丙]\s?(?:第\s?)?\d", ctx):
        return True
    if re.search(r"(?:最高裁|地方裁判所|高等裁判所|最判|最大判|地判|高判|決定)", ctx):
        return True
    return False


AUTHOR = re.compile(r"([一-龥々ぁ-んァ-ヶA-Za-z][一-龥々ぁ-んァ-ヶA-Za-z＝=・\u30fb]{1,24})\s*$")
NOISE_HEAD = re.compile(r"(?:参照|前掲|例えば|同|注|see|See)\s*[,、]?\s*$")


def spans_for(text):
    """鉤括弧の直後60文字に書誌情報が続くものだけを引用として切り出す。"""
    text = HTML.sub(" ", text)
    # 「主要業績」等の見出し以降しばらくは、意見書執筆者自身の著作リストとみなす
    cv_zones = [m.start() for m in re.finditer("|".join(CV_MARK), text)]
    in_cv = lambda pos: any(z <= pos <= z + 4000 for z in cv_zones)
    out = []
    for m in re.finditer(r"[『「]([^』」\n]{2,60})[』」]", text):
        title = norm(m.group(1))
        if len(title) < 3:
            continue
        tail = re.sub(r"\s+", " ", text[m.end():m.end() + 60])
        head = re.sub(r"\s+", " ", text[max(0, m.start() - 40):m.start()])
        ctx = (head + m.group(0) + tail).strip()
        # 書誌情報はタイトルの「直後」に来る。離れていたら引用ではなく本文中の強調。
        has_pub = any(p in tail[:20] for p in PUBLISHERS)
        # (有斐閣、2023年) のように括弧に入った発行年
        year_paren = bool(re.match(r"[^。]{0,10}[（(〔\[【][^）)〕\]】]{0,24}"
                                   r"(?:1[89]\d\d|20\d\d|(?:平成|昭和|令和)\s?\d{1,2})\s?年?", tail))
        # 『書名』252頁 のように頁がすぐ続く
        page_near = bool(re.match(r"[^。]{0,10}\d[\d,\s]{0,6}(?:頁|ページ)", tail))
        # 雑誌名は「まるごと一致」を要求する。『都市計画案』が雑誌『都市計画』に
        # 引っかかるのを防ぐため、部分一致は採らない
        has_jnl_self = title in JOURNALS or any(
            title.startswith(j) and len(title) <= len(j) + 8 for j in JOURNALS)
        has_jnl_tail = any(re.search(re.escape(j) + r"[』」]?\s*\d+\s*[巻号]", tail)
                           or f"『{j}』" in tail for j in JOURNALS)
        is_dq = m.group(0)[0] == "『"
        if is_dq:
            ok = has_pub or year_paren or page_near
            kind = "論文（雑誌掲載）" if (has_jnl_self or has_jnl_tail) else "書籍"
        else:
            # 「論文名」の後ろに 掲載誌 が続く形だけを採る
            ok = has_jnl_tail or ("『" in tail[:12] and PAGE.search(tail)) \
                 or (VOLNUM.search(tail[:20]) and PAGE.search(tail))
            kind = "論文（雑誌掲載）"
        if not ok or excluded(ctx):
            continue
        if in_cv(m.start()):
            kind = "執筆者の業績（引用ではない）"
        # 著者らしき部分と、出典（出版社・年・頁）を分けて取る
        h = NOISE_HEAD.sub("", head.strip())
        am = AUTHOR.search(h)
        author = am.group(1).strip("・＝=") if am else ""
        sm = re.search(r"^[^。]{0,60}?(?:頁|ページ|\))", tail)
        source = (sm.group(0) if sm else tail[:40]).strip(" 、,。")
        out.append((kind, title, ctx, author, source, m.group(0)[0]))
    for m in EN_CITE.finditer(text):
        s = re.sub(r"\s+", " ", m.group(0)).strip()
        if PAGE.search(s) or YEAR.search(s) or "Press" in s:
            kind = "執筆者の業績（引用ではない）" if in_cv(m.start()) else "英語文献"
            out.append((kind, s[:80], s, "", "", ""))
    return out


docs_meta = {}
for cid in TARGETS:
    for d in json.load(open(os.path.join(HERE, "cache", f"docs_{cid}.json")))["documents"]:
        docs_meta[d["id"]] = (cid, d.get("file_name", ""))
cases = {c["id"]: c["title"] for c in
         json.load(open(os.path.join(HERE, "cache", "cases_list.json")))["cases"]}

found, n_doc, n_txt = [], 0, 0
for doc_id, (cid, fname) in sorted(docs_meta.items()):
    p = os.path.join(HERE, "cache", "text", f"{doc_id}.json")
    n_doc += 1
    if not os.path.exists(p):
        continue
    text = json.load(open(p)).get("text") or ""
    if not text:
        continue
    n_txt += 1
    for kind, title, ctx, author, source, br in spans_for(text):
        found.append({"case": cid, "case_title": cases.get(cid, ""), "doc": doc_id,
                      "doc_name": fname, "kind": kind, "title": title,
                      "author": author, "source": source, "context": ctx,
                      "bracket": br})

groups = collections.defaultdict(list)
for r in found:
    groups[r["title"][:30]].append(r)
merged = []
for k, rs in groups.items():
    best = max(rs, key=lambda r: len(r["context"]))
    merged.append({**best, "出現回数": len(rs),
                   "出現ケース": sorted({r["case"] for r in rs}),
                   "出現資料数": len({r["doc"] for r in rs})})
ORDER = {"書籍": 0, "論文（雑誌掲載）": 1, "英語文献": 2, "執筆者の業績（引用ではない）": 3}
merged.sort(key=lambda r: (ORDER.get(r["kind"], 9), -r["出現回数"], r["title"]))

json.dump(merged, open(os.path.join(HERE, "out_citations.json"), "w"),
          ensure_ascii=False, indent=1)
with open(os.path.join(HERE, "out_引用文献_候補.csv"), "w",
          encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["種類", "著者", "タイトル", "出典", "出現回数", "出現資料数",
                "ケースID", "ケース名", "引用していた資料", "引用箇所の前後"])
    for r in merged:
        w.writerow([r["kind"], r["author"], r["title"], r["source"], r["出現回数"],
                    r["出現資料数"], "/".join(r["出現ケース"]), r["case_title"],
                    r["doc_name"], r["context"]])

print(f"対象 {len(TARGETS)}ケース / 資料 {n_doc}件 / 本文が取れた {n_txt}件")
print(f"引用 のべ {len(found)}件 → 重複をまとめて {len(merged)}件")
for k, n in collections.Counter(r["kind"] for r in merged).most_common():
    print(f"  {k}: {n}件")
print()
cur = None
for r in merged:
    if r["kind"] != cur:
        cur = r["kind"]; print(f"\n########## {cur} ##########")
    a = f"{r['author']} " if r["author"] else ""
    o, c = ("「", "」") if r.get("bracket") == "「" else ("『", "』")
    if not r.get("bracket"):
        o = c = ""
    print(f"  [{r['出現回数']:>2}回] {a}{o}{r['title'][:44]}{c} {r['source'][:40]}")
