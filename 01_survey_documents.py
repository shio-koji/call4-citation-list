#!/usr/bin/env python3
"""全ケースの訴訟資料を棚卸しする。
何件あり、うち何件が has_text（テキスト抽出済み）かを数えるだけ。本文はまだ落とさない。
"""
import json, os, time, urllib.request, urllib.error

URL = "https://www.call4.jp/flight_api/mcp/sse"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)


def call4(name, args):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": name, "arguments": args}}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            outer = json.loads(r.read())
    except urllib.error.HTTPError as e:      # 失敗も 500 で返るので本文を読む
        outer = json.loads(e.read())
    if "error" in outer:
        raise RuntimeError(outer["error"])
    res = outer["result"]
    if res.get("isError"):
        raise RuntimeError(res["content"][0]["text"])
    return json.loads(res["content"][0]["text"])


def cached(path, fn):
    p = os.path.join(CACHE, path)
    if os.path.exists(p):
        return json.load(open(p))
    v = fn()
    json.dump(v, open(p, "w"), ensure_ascii=False)
    time.sleep(0.1)
    return v


cases = cached("cases_list.json", lambda: call4("search_cases", {"query": "", "search_mode": "or"}))
print(f"公開ケース {cases['total']} 件")

rows = []
for i, c in enumerate(cases["cases"], 1):
    cid = c["id"]
    try:
        docs = cached(f"docs_{cid}.json", lambda: call4("list_documents", {"id": cid}))
    except RuntimeError as e:
        print(f"  !! {cid} {e}")
        rows.append({"id": cid, "title": c["title"], "error": str(e), "n": 0, "n_text": 0})
        continue
    d = docs.get("documents", [])
    rows.append({
        "id": cid, "title": c["title"], "tags": c.get("tags", []),
        "n": len(d),
        "n_text": sum(1 for x in d if x.get("has_text")),
        "categories": sorted({str(x.get("material_category")) for x in d}),
    })
    print(f"[{i:>3}/{cases['total']}] {cid} 資料{len(d):>3}件 うちtext {rows[-1]['n_text']:>3}件  {c['title'][:34]}")

json.dump(rows, open(os.path.join(HERE, "out_survey.json"), "w"), ensure_ascii=False, indent=1)

n_doc = sum(r["n"] for r in rows)
n_txt = sum(r["n_text"] for r in rows)
print("=" * 60)
print(f"ケース {len(rows)} 件 / 資料 {n_doc} 件 / テキスト化済み {n_txt} 件 ({n_txt/max(n_doc,1):.1%})")
print(f"資料0件のケース: {sum(1 for r in rows if r['n']==0)} 件")
print(f"テキスト0件のケース: {sum(1 for r in rows if r['n_text']==0)} 件")
