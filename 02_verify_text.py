#!/usr/bin/env python3
"""has_text フラグが本当か、実際に fetch_document_text して確かめる。
全件は6825リクエストになるので、ケースをまたいでサンプリングする。
失敗（PDF解析不能・暗号化PDFなど）も記録する。
"""
import json, os, random, time, urllib.request, urllib.error

URL = "https://www.call4.jp/flight_api/mcp/sse"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
TXT = os.path.join(CACHE, "text"); os.makedirs(TXT, exist_ok=True)


def call4(name, args):
    """成功なら dict を返す。失敗は {"_error": "..."} を返す（例外にしない）。
    API は失敗を HTTP 500 + error で返すほか、content[0].text が文字列でないこともある。
    """
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": name, "arguments": args}}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                outer = json.loads(r.read())
        except urllib.error.HTTPError as e:
            outer = json.loads(e.read())
    except Exception as e:
        return {"_error": f"transport: {e}"}
    if "error" in outer:
        return {"_error": str(outer["error"].get("message", outer["error"]))}
    res = outer.get("result", {})
    if res.get("isError"):
        return {"_error": str(res["content"][0].get("text"))}
    inner = res.get("content", [{}])[0].get("text")
    if not isinstance(inner, str):
        return {"_error": f"unexpected content type: {type(inner).__name__} {inner!r}"}
    try:
        return json.loads(inner)
    except json.JSONDecodeError:
        return {"text": inner}


def get_text(doc_id):
    p = os.path.join(TXT, f"{doc_id}.json")
    if os.path.exists(p):
        return json.load(open(p))
    v = call4("fetch_document_text", {"id": doc_id})
    json.dump(v, open(p, "w"), ensure_ascii=False)   # 失敗も記録して再試行しない
    time.sleep(0.1)
    return v


# 各ケースから has_text=True / False をそれぞれ最大2件ずつ拾う
random.seed(0)
sample = []
for f in sorted(os.listdir(CACHE)):
    if not f.startswith("docs_"):
        continue
    cid = f[5:-5]
    docs = json.load(open(os.path.join(CACHE, f))).get("documents", [])
    yes = [d for d in docs if d.get("has_text")]
    no = [d for d in docs if not d.get("has_text")]
    for d in random.sample(yes, min(2, len(yes))) + random.sample(no, min(2, len(no))):
        sample.append((cid, d))

print(f"サンプル {len(sample)} 件を実取得して検証します")
rows = []
for i, (cid, d) in enumerate(sample, 1):
    r = get_text(d["id"])
    text = r.get("text") or ""
    rows.append({"case": cid, "doc": d["id"], "file_name": d.get("file_name", ""),
                 "material_category": d.get("material_category"),
                 "has_text": bool(d.get("has_text")), "len": len(text),
                 "is_extracted": r.get("is_extracted"), "error": r.get("_error", "")})
    if i % 50 == 0:
        print(f"  {i}/{len(sample)}")

json.dump(rows, open(os.path.join(HERE, "out_verify.json"), "w"), ensure_ascii=False, indent=1)

y = [r for r in rows if r["has_text"]]
n = [r for r in rows if not r["has_text"]]
print("=" * 64)
for label, g in (("has_text=True ", y), ("has_text=False", n)):
    if not g:
        continue
    ok = [r for r in g if r["len"] > 0]
    print(f"{label} {len(g):>3}件 → 本文あり {len(ok):>3} / 空 {sum(1 for r in g if r['len']==0 and not r['error']):>3} / エラー {sum(1 for r in g if r['error']):>3}")
    if ok:
        L = sorted(r["len"] for r in ok)
        print(f"                  文字数 中央値 {L[len(L)//2]:,} / 最小 {L[0]:,} / 最大 {L[-1]:,}")
errs = {}
for r in rows:
    if r["error"]:
        errs[r["error"][:60]] = errs.get(r["error"][:60], 0) + 1
if errs:
    print("エラー内訳:")
    for k, v in sorted(errs.items(), key=lambda x: -x[1]):
        print(f"  {v:>3}件  {k}")
