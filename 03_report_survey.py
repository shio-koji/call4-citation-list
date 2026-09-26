#!/usr/bin/env python3
"""棚卸し結果を人が読める形にする。CSV と Markdown を出す。"""
import json, os, csv, collections

HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, "out_survey.json")))
CAT = {"1": "書面（訴状・準備書面など）", "2": "証拠", "3": "判決・決定", "4": "その他"}

# --- CSV（Excelで開けるよう BOM 付き） ---
with open(os.path.join(HERE, "out_ケース別_資料数.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ケースID", "タイトル", "資料件数", "テキスト化済み", "テキスト化率", "URL", "タグ"])
    for r in sorted(rows, key=lambda x: -x["n"]):
        rate = f"{r['n_text']/r['n']:.0%}" if r["n"] else "-"
        w.writerow([r["id"], r["title"], r["n"], r["n_text"], rate,
                    f"https://www.call4.jp/info.php?type=items&id={r['id']}",
                    "/".join(r.get("tags", []))])

n_doc = sum(r["n"] for r in rows)
n_txt = sum(r["n_text"] for r in rows)
zero = [r for r in rows if r["n"] == 0]
notext = [r for r in rows if r["n"] and r["n_text"] == 0]
partial = sorted([r for r in rows if r["n"] and r["n_text"] < r["n"]], key=lambda x: x["n_text"]/x["n"])

# 資料カテゴリの分布
cat = collections.Counter()
for f in os.listdir(os.path.join(HERE, "cache")):
    if f.startswith("docs_"):
        for d in json.load(open(os.path.join(HERE, "cache", f))).get("documents", []):
            cat[str(d.get("material_category"))] += 1

L = []
a = L.append
a("# 中間報告① 訴訟資料はどれだけ取れるか\n")
a("CALL4のAPIから、公開されている全ケースの訴訟資料を棚卸しした結果です。")
a("「テキスト化済み」＝PDFから本文テキストが抽出されていて、**機械で中身を読める**状態のもの。\n")
a("## 結論\n")
a(f"- 公開ケース **{len(rows)}件** すべてについて資料一覧が取得できた")
a(f"- 資料は合計 **{n_doc:,}件**、うちテキスト化済みは **{n_txt:,}件（{n_txt/n_doc:.1%}）**")
a(f"- 資料が1件も無いケースは **{len(zero)}件** だけ")
a(f"- 1ケースあたりの資料数は中央値 **{sorted(r['n'] for r in rows)[len(rows)//2]}件**、最大 **{max(r['n'] for r in rows)}件**\n")
a("つまり、**「訴訟資料が引用している論文を抽出する」ための材料はほぼ揃っている**、と言えます。\n")
a("## 資料の種類\n")
a("| 種類 | 件数 |")
a("|---|---:|")
for k, v in cat.most_common():
    a(f"| {CAT.get(k, f'不明({k})')} | {v:,} |")
a("")
a("## 取れなかった／不完全なケース\n")
if zero:
    a("**資料が0件**（訴訟資料が未公開）")
    a("")
    for r in zero:
        a(f"- `{r['id']}` {r['title']}")
    a("")
if notext:
    a("**資料はあるがテキストが0件**")
    a("")
    for r in notext:
        a(f"- `{r['id']}` {r['title']}（資料{r['n']}件）")
    a("")
a("**一部テキスト化されていないケース（率の低い順に10件）**\n")
a("| ケースID | タイトル | 資料 | うちtext | 率 |")
a("|---|---|---:|---:|---:|")
for r in partial[:10]:
    a(f"| `{r['id']}` | {r['title'][:30]} | {r['n']} | {r['n_text']} | {r['n_text']/r['n']:.0%} |")
a("")
a("## 資料が多いケース 上位15件\n")
a("| ケースID | タイトル | 資料 | うちtext |")
a("|---|---|---:|---:|")
for r in sorted(rows, key=lambda x: -x["n"])[:15]:
    a(f"| `{r['id']}` | {r['title'][:34]} | {r['n']} | {r['n_text']} |")
a("")
a("---\n")
a("全96ケースの内訳は `out_ケース別_資料数.csv`（Excelで開けます）。")
a("生データは `cache/docs_<ケースID>.json`（APIの応答そのまま）。")

open(os.path.join(HERE, "中間報告01_訴訟資料の取得可否.md"), "w").write("\n".join(L))
print("\n".join(L[:40]))
