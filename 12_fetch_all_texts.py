#!/usr/bin/env python3
"""全96ケース・全訴訟資料の本文を取得する。

1件あたり中央値5秒かかる（サーバー側で抽出処理をしているため）。
逐次だと8時間を超えるので、同時3本までに抑えて回す。それ以上は負荷をかけすぎる。

キャッシュ済みは飛ばすので、途中で止めても再実行で続きから走る。
失敗も記録して再試行しない（0バイトのPDFや動画など、何度叩いても取れないものがあるため）。
"""
import json, os, queue, sys, threading, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
TXT = os.path.join(HERE, "cache", "text"); os.makedirs(TXT, exist_ok=True)
URL = "https://www.call4.jp/flight_api/mcp/sse"
WORKERS = 3
PAUSE = 0.15          # 1リクエストごとに各ワーカーが待つ秒数


def call4(name, args):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": name, "arguments": args}}).encode()
    req = urllib.request.Request(URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                outer = json.loads(r.read())
        except urllib.error.HTTPError as e:
            outer = json.loads(e.read())
    except Exception as e:
        return {"_error": f"transport: {str(e)[:80]}"}
    if "error" in outer:
        return {"_error": str(outer["error"].get("message", outer["error"]))[:120]}
    res = outer.get("result", {})
    if res.get("isError"):
        return {"_error": str(res["content"][0].get("text"))[:120]}
    inner = res.get("content", [{}])[0].get("text")
    if not isinstance(inner, str):
        return {"_error": f"unexpected content type: {type(inner).__name__}"}
    try:
        return json.loads(inner)
    except json.JSONDecodeError:
        return {"text": inner}


# 取得対象を集める
have = {f[:-5] for f in os.listdir(TXT) if f.endswith(".json")}
todo = []
for f in sorted(os.listdir(os.path.join(HERE, "cache"))):
    if not f.startswith("docs_"):
        continue
    for d in json.load(open(os.path.join(HERE, "cache", f)))["documents"]:
        if d["id"] not in have:
            todo.append(d["id"])
todo = sorted(set(todo))

print(f"取得済み {len(have)}件 / これから {len(todo)}件 / 同時 {WORKERS}本", flush=True)
if not todo:
    sys.exit(0)

q = queue.Queue()
for i in todo:
    q.put(i)
lock = threading.Lock()
state = {"done": 0, "ok": 0, "ng": 0, "t0": time.time()}


def worker():
    while True:
        try:
            doc_id = q.get_nowait()
        except queue.Empty:
            return
        r = call4("fetch_document_text", {"id": doc_id})
        json.dump(r, open(os.path.join(TXT, f"{doc_id}.json"), "w"), ensure_ascii=False)
        with lock:
            state["done"] += 1
            if r.get("text"):
                state["ok"] += 1
            else:
                state["ng"] += 1
            n = state["done"]
            if n % 50 == 0 or n == len(todo):
                el = time.time() - state["t0"]
                rate = n / el
                eta = (len(todo) - n) / rate / 60
                print(f"  {n:>5}/{len(todo)}  本文あり {state['ok']:>5}  空/失敗 {state['ng']:>4}  "
                      f"{rate*60:.0f}件/分  残り約{eta:.0f}分", flush=True)
        time.sleep(PAUSE)


ts = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
for t in ts:
    t.start()
for t in ts:
    t.join()

el = time.time() - state["t0"]
print(f"完了 {state['done']}件 / 本文あり {state['ok']}件 / 空・失敗 {state['ng']}件 "
      f"/ 所要 {el/3600:.2f}時間", flush=True)
