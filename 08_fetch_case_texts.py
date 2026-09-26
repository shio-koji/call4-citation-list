#!/usr/bin/env python3
"""試作の対象ケースについて、資料の本文をすべて取得する。
has_text=False でも2割は取れるので、フラグに関係なく全部叩く。
"""
import json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
TXT = os.path.join(HERE, "cache", "text"); os.makedirs(TXT, exist_ok=True)
URL = "https://www.call4.jp/flight_api/mcp/sse"

TARGETS = ["I0000090", "I0000111", "I0000120", "I0000159"]


def call4(name, args):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": name, "arguments": args}}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
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
        return {"_error": f"unexpected content type: {type(inner).__name__}"}
    try:
        return json.loads(inner)
    except json.JSONDecodeError:
        return {"text": inner}


total = ok = 0
for cid in TARGETS:
    docs = json.load(open(os.path.join(HERE, "cache", f"docs_{cid}.json")))["documents"]
    got = 0
    for d in docs:
        total += 1
        p = os.path.join(TXT, f"{d['id']}.json")
        if not os.path.exists(p):
            json.dump(call4("fetch_document_text", {"id": d["id"]}),
                      open(p, "w"), ensure_ascii=False)
            time.sleep(0.1)
        if (json.load(open(p)).get("text") or ""):
            got += 1
    ok += got
    print(f"{cid}  資料{len(docs):>3}件 → 本文が取れた {got:>3}件")
print(f"合計 {total}件中 {ok}件（{ok/total:.0%}）の本文を確保")
