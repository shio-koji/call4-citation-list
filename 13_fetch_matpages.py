#!/usr/bin/env python3
"""全96ケースの資料一覧ページHTMLを取り、資料ID → PDFのURL の対応表を作る。

PDFのURLはAPIには含まれないので、ここだけHTMLから拾う。
資料IDは summaryModal-<資料ID> から取れるが、要約が無い資料には出ないので
資料名でのフォールバックを併用する（15ケース2,354件で99.6%対応を確認済み）。
"""
import json, os, re, time, collections, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MAT = os.path.join(HERE, "cache", "matpage"); os.makedirs(MAT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
norm = lambda s: re.sub(r"\s+", " ", s or "").strip()

cases = json.load(open(os.path.join(HERE, "cache", "cases_list.json")))["cases"]
out, stat = {}, collections.Counter()

for i, c in enumerate(cases, 1):
    cid = c["id"]
    p = os.path.join(MAT, f"{cid}.html")
    if not os.path.exists(p):
        u = ("https://www.call4.jp/search.php?type=material&run=true"
             f"&items_id_PAL%5B%5D=match+comp&items_id={cid}")
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=90) as r:
                open(p, "wb").write(r.read())
        except Exception as e:
            print(f"  !! {cid} {e}")
            continue
        time.sleep(0.3)
    h = open(p, encoding="utf-8", errors="replace").read()
    byid, byname = {}, collections.defaultdict(list)
    for b in re.split(r'<li class="w-100">', h)[1:]:
        m = re.search(r'href="(file/[^"]+)"', b)
        if not m:
            continue
        url = "https://www.call4.jp/" + m.group(1)
        mi = re.search(r"summaryModal-(\d{6})", b)
        mn = re.search(r'<span class="name">(.*?)</span>', b, re.S)
        if mi:
            byid[mi.group(1)] = url
        if mn:
            byname[norm(mn.group(1))].append(url)

    dp = os.path.join(HERE, "cache", f"docs_{cid}.json")
    if not os.path.exists(dp):
        continue
    for d in json.load(open(dp))["documents"]:
        if d["id"] in byid:
            out[d["id"]] = byid[d["id"]]; stat["ID一致"] += 1
        else:
            cand = byname.get(norm(d.get("file_name", "")), [])
            if len(cand) == 1:
                out[d["id"]] = cand[0]; stat["資料名で一致"] += 1
            elif len(cand) > 1:
                stat["同名が複数で曖昧"] += 1
            else:
                stat["対応づかず"] += 1
    if i % 20 == 0:
        print(f"  {i}/{len(cases)} ケース処理", flush=True)

json.dump(out, open(os.path.join(HERE, "cache", "pdf_urls.json"), "w"), ensure_ascii=False)
tot = sum(stat.values())
print(f"資料 {tot}件 → PDFのURLが分かったもの {len(out)}件 ({len(out)/tot:.1%})")
for k, v in stat.most_common():
    print(f"  {k}: {v}件")
