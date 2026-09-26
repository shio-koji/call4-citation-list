#!/usr/bin/env python3
"""本文が取れなかった資料について、PDFを実際に落として素性を調べる。
OCRできるか以前に「ファイルが存在するか」「暗号化されているか」「画像か」を見る。
資料IDとPDFの対応は、HTMLの summaryModal-<資料ID> を第一に、無ければ資料名で突き合わせる。
"""
import json, os, re, time, collections, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "cache", "pdf"); os.makedirs(PDF, exist_ok=True)
MAT = os.path.join(HERE, "cache", "matpage"); os.makedirs(MAT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
norm = lambda s: re.sub(r"\s+", " ", s or "").strip()


def material_page(cid):
    p = os.path.join(MAT, f"{cid}.html")
    if not os.path.exists(p):
        u = ("https://www.call4.jp/search.php?type=material&run=true"
             f"&items_id_PAL%5B%5D=match+comp&items_id={cid}")
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60) as r:
            open(p, "wb").write(r.read())
        time.sleep(0.3)
    h = open(p, encoding="utf-8", errors="replace").read()
    byid, byname = {}, collections.defaultdict(list)
    for b in re.split(r'<li class="w-100">', h)[1:]:
        u = re.search(r'href="(file/[^"]+)"', b)
        if not u:
            continue
        url = "https://www.call4.jp/" + u.group(1)
        i = re.search(r"summaryModal-(\d{6})", b)
        n = re.search(r'<span class="name">(.*?)</span>', b, re.S)
        if i:
            byid[i.group(1)] = url
        if n:
            byname[norm(n.group(1))].append(url)
    return byid, byname


def url_for(cid, doc_id, file_name, cache={}):
    if cid not in cache:
        cache[cid] = material_page(cid)
    byid, byname = cache[cid]
    if doc_id in byid:
        return byid[doc_id]
    c = byname.get(norm(file_name), [])
    return c[0] if len(c) == 1 else None


def probe(doc_id, url):
    ext = os.path.splitext(url)[1].lower()
    if ext != ".pdf":
        return {"判定": f"PDFではない（{ext}）"}
    p = os.path.join(PDF, f"{doc_id}{ext}")
    if not os.path.exists(p):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                open(p, "wb").write(r.read())
            time.sleep(0.3)
        except Exception as e:
            return {"判定": f"ダウンロード失敗: {str(e)[:40]}"}
    info = {"bytes": os.path.getsize(p)}
    try:
        import pypdf
        rd = pypdf.PdfReader(p)
        info["暗号化"] = rd.is_encrypted
        if rd.is_encrypted:
            info["空パスワードで解除"] = bool(rd.decrypt(""))
        info["ページ数"] = len(rd.pages)
        t = "".join((pg.extract_text() or "") for pg in rd.pages[:10])
        info["PDF内の文字数(先頭10p)"] = len(re.sub(r"\s", "", t))
        info["判定"] = ("テキスト層あり→OCR不要" if info["PDF内の文字数(先頭10p)"] > 200
                       else "画像スキャン→OCRが必要")
    except Exception as e:
        info["判定"] = f"PDFとして開けない: {str(e)[:50]}"
    return info


targets = [r for r in json.load(open(os.path.join(HERE, "out_verify.json")))
           if r["error"] or r["len"] == 0]
byk, picked = collections.defaultdict(list), []
for r in targets:
    k = r["error"][:45] if r["error"] else "(空文字が返った)"
    if len(byk[k]) < 3:
        byk[k].append(r); picked.append((k, r))

print(f"本文が取れなかった資料 {len(targets)}件 から {len(picked)}件を調査\n")
rows = []
for k, r in picked:
    url = url_for(r["case"], r["doc"], r["file_name"])
    info = {"判定": "HTMLにもファイルが無い"} if not url else probe(r["doc"], url)
    rows.append({"分類": k, "case": r["case"], "doc": r["doc"],
                 "file_name": r["file_name"], "url": url, **info})
    print(f"[{k}]")
    print(f"  {r['case']} 資料{r['doc']} {r['file_name'][:36]}")
    print(f"  → {info}")

json.dump(rows, open(os.path.join(HERE, "out_failed_pdfs.json"), "w"),
          ensure_ascii=False, indent=1)
