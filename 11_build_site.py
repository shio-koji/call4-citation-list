#!/usr/bin/env python3
"""抽出した引用文献を、誰にでも見せられる1枚のHTMLにする。

GitHub Pages で配れるよう、外部ファイルに依存しない自己完結HTMLにしてある。
出力先は docs/index.html（GitHub Pages の「mainブランチの/docs」設定で公開できる）。
"""
import json, os, re, html, collections, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs"); os.makedirs(DOCS, exist_ok=True)
MAT = os.path.join(HERE, "cache", "matpage"); os.makedirs(MAT, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
TARGETS = ["I0000090", "I0000111", "I0000120", "I0000159"]
CV = "執筆者の業績（引用ではない）"
norm = lambda s: re.sub(r"\s+", " ", s or "").strip()


def pdf_map(cid):
    """資料ID → PDFのURL。HTMLから拾う（APIには無い）。"""
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


maps = {c: pdf_map(c) for c in TARGETS}


def pdf_for(cid, doc_id, name):
    byid, byname = maps[cid]
    if doc_id in byid:
        return byid[doc_id]
    c = byname.get(norm(name), [])
    return c[0] if len(c) == 1 else ""


rows = json.load(open(os.path.join(HERE, "out_citations.json")))
survey = {r["id"]: r for r in json.load(open(os.path.join(HERE, "out_survey.json")))}
for r in rows:
    r["pdf"] = pdf_for(r["case"], r["doc"], r["doc_name"])
    r["case_url"] = f"https://www.call4.jp/info.php?type=items&id={r['case']}"

real = [r for r in rows if r["kind"] != CV]
n_doc = sum(survey[c]["n"] for c in TARGETS)
kinds = collections.Counter(r["kind"] for r in rows)
case_names = {r["case"]: r["case_title"] for r in rows}

DATA = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
TILES = [("対象ケース", len(TARGETS), "件"), ("読み込んだ訴訟資料", n_doc, "件"),
         ("抽出した学術文献", len(real), "件"),
         ("うち論文（雑誌掲載）", kinds.get("論文（雑誌掲載）", 0), "件")]

tiles_html = "\n".join(
    f'<div class="tile"><div class="tile-n">{v:,}<span class="tile-u">{u}</span></div>'
    f'<div class="tile-l">{html.escape(l)}</div></div>' for l, v, u in TILES)
bycase = collections.Counter()
for r in real:
    for c in r["出現ケース"]:
        bycase[c] += 1
cases_html = "\n".join(
    f'<li><a href="https://www.call4.jp/info.php?type=items&amp;id={c}" target="_blank" '
    f'rel="noopener">{html.escape(case_names.get(c, c))}</a>'
    f'<span class="cs">資料{survey[c]["n"]}件 · 引用{bycase.get(c, 0)}件</span></li>'
    for c in TARGETS)

case_opts = "\n".join(
    f'<option value="{c}">{html.escape(case_names.get(c, c))[:34]}</option>' for c in TARGETS)
kind_opts = "\n".join(
    f'<option value="{html.escape(k)}">{html.escape(k)}（{n}）</option>'
    for k, n in kinds.most_common())

HTML_DOC = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CALL4 訴訟資料の引用文献リスト（試作）</title>
<meta name="description" content="CALL4に公開されている公共訴訟の訴訟資料が引用している学術文献を抽出したリストの試作版。">
<style>
:root {{
  color-scheme: light dark;
  --surface: #fcfcfb; --card: #ffffff; --line: #e7e6e2;
  --ink: #0b0b0b; --ink2: #52514e; --ink3: #8a8981;
  --accent: #2a78d6; --accent-soft: #eaf2fd; --warn-bg: #fdf6e6; --warn-line: #eda100;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --surface: #1a1a19; --card: #232321; --line: #333330;
    --ink: #ffffff; --ink2: #c3c2b7; --ink3: #8a8981;
    --accent: #3987e5; --accent-soft: #1d2a3b; --warn-bg: #2b2517; --warn-line: #c98500;
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--surface); color: var(--ink);
  font-family: "Hiragino Sans", "Yu Gothic", system-ui, sans-serif;
  line-height: 1.75; font-size: 15px;
}}
.wrap {{ max-width: 1120px; margin: 0 auto; padding: 40px 20px 80px; }}
h1 {{ font-size: 25px; margin: 0 0 6px; letter-spacing: .01em; }}
.sub {{ color: var(--ink2); margin: 0 0 26px; }}
a {{ color: var(--accent); }}
.cases {{ margin: 0 0 26px; }}
.cases h2 {{ font-size: 13px; font-weight: 600; color: var(--ink3); margin: 0 0 8px; letter-spacing: .04em; }}
.cases ol {{ margin: 0; padding: 0; list-style: none; counter-reset: c; }}
.cases li {{
  counter-increment: c; display: flex; flex-wrap: wrap; align-items: baseline;
  gap: 4px 10px; padding: 7px 0 7px 26px; position: relative;
  border-bottom: 1px solid var(--line); font-size: 14.5px;
}}
.cases li:last-child {{ border-bottom: 0; }}
.cases li::before {{
  content: counter(c); position: absolute; left: 0; top: 7px;
  color: var(--ink3); font-size: 12px; font-variant-numeric: tabular-nums;
}}
.cases .cs {{ color: var(--ink3); font-size: 12.5px; }}
.note {{
  background: var(--warn-bg); border-left: 3px solid var(--warn-line);
  padding: 14px 18px; border-radius: 0 6px 6px 0; margin: 0 0 28px;
  color: var(--ink2); font-size: 14px;
}}
.note b {{ color: var(--ink); }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 0 0 30px; }}
.tile {{ background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 16px 18px; }}
.tile-n {{ font-size: 30px; font-weight: 650; letter-spacing: -.01em; line-height: 1.2; }}
.tile-u {{ font-size: 14px; font-weight: 400; color: var(--ink2); margin-left: 3px; }}
.tile-l {{ font-size: 13px; color: var(--ink2); margin-top: 2px; }}
.controls {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 0 0 6px; }}
input[type=search], select {{
  font: inherit; font-size: 14px; padding: 9px 12px; color: var(--ink);
  background: var(--card); border: 1px solid var(--line); border-radius: 7px;
}}
input[type=search] {{ flex: 1 1 280px; }}
.count {{ color: var(--ink3); font-size: 13px; margin: 0 0 14px; }}
.item {{ border-bottom: 1px solid var(--line); padding: 15px 2px; }}
.item:last-child {{ border-bottom: 0; }}
.cite {{ font-size: 15.5px; }}
.cite .au {{ color: var(--ink); font-weight: 600; }}
.cite .ti {{ color: var(--ink); }}
.cite .so {{ color: var(--ink2); }}
.meta {{ margin-top: 5px; font-size: 12.5px; color: var(--ink3); display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: center; }}
.chip {{
  display: inline-block; padding: 1px 9px; border-radius: 999px; font-size: 11.5px;
  background: var(--accent-soft); color: var(--accent); border: 1px solid transparent;
}}
.chip.cv {{ background: transparent; border-color: var(--line); color: var(--ink3); }}
details {{ margin-top: 7px; }}
summary {{ cursor: pointer; color: var(--ink3); font-size: 12.5px; }}
.ctx {{
  margin-top: 7px; padding: 11px 14px; background: var(--card); border: 1px solid var(--line);
  border-radius: 6px; font-size: 13px; color: var(--ink2); line-height: 1.85;
}}
.empty {{ padding: 50px 0; text-align: center; color: var(--ink3); }}
footer {{ margin-top: 46px; padding-top: 22px; border-top: 1px solid var(--line); font-size: 13px; color: var(--ink3); }}
footer a {{ color: var(--ink2); }}
</style>
</head>
<body>
<div class="wrap">

<h1>CALL4 訴訟資料の引用文献リスト</h1>
<p class="sub">公共訴訟プラットフォーム <a href="https://www.call4.jp/">CALL4</a> に公開されている訴訟資料が、
どんな学術文献を引用しているかを機械的に抽出したものです。</p>

<section class="cases">
<h2>対象の4ケース</h2>
<ol>
{cases_html}
</ol>
</section>

<div class="note">
<b>これは試作版です。</b> 全96ケースのうち<b>4ケースだけ</b>を対象にしています。
抽出は自動処理で、人手による確認を経ていません。誤って拾ったもの・取りこぼしたものが含まれます。
<br>とくに <code>前掲注(24)</code> のような2回目以降の省略引用は拾えていません。
引用の正確な内容は、かならず出典元の資料そのものをご確認ください。
</div>

<div class="tiles">{tiles_html}</div>

<div class="controls">
  <input type="search" id="q" placeholder="著者名・書名・雑誌名で絞り込む（例: 芦部、憲法、ジュリスト）">
  <select id="kind"><option value="">すべての種類</option>{kind_opts}</select>
  <select id="case"><option value="">すべてのケース</option>{case_opts}</select>
</div>
<p class="count" id="count"></p>
<div id="list"></div>

<footer>
<p><b>作り方</b> — CALL4のAPIで訴訟資料の本文を取得し、
「著者『書名』(出版社、年)頁」という書式のうち、鉤括弧の直後に書誌情報が続くものを引用として抽出しています。
訴訟書面の自己参照（<code>準備書面12頁</code>）、判例（<code>民集59巻7号2087頁</code>）、
証拠番号（<code>甲15・3頁</code>）は除外しました。判例の抽出は今回の対象外です。</p>
<p><b>「執筆者の業績」とは</b> — 意見書の末尾には執筆者自身の経歴と主要著作が載っています。
これは訴訟で引用された文献ではないので、種類を分けてあります。</p>
<p><b>データの出どころ</b> — すべて <a href="https://www.call4.jp/">CALL4</a> の公開データです。
訴訟資料の権利はCALL4および各ケースの関係者にあります。
引用箇所の前後の文章は、どの文献を指しているかを確認できるようにするための短い抜粋です。</p>
</footer>

</div>
<script>
const DATA = {DATA};
const q = document.getElementById('q'), fk = document.getElementById('kind'),
      fc = document.getElementById('case'), list = document.getElementById('list'),
      count = document.getElementById('count');
const esc = s => (s||'').replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
const CV = '執筆者の業績（引用ではない）';

function cite(r) {{
  const o = r.bracket === '「' ? '「' : (r.bracket ? '『' : ''),
        c = r.bracket === '「' ? '」' : (r.bracket ? '』' : '');
  return (r.author ? `<span class="au">${{esc(r.author)}}</span> ` : '')
       + `<span class="ti">${{o}}${{esc(r.title)}}${{c}}</span>`
       + (r.source ? ` <span class="so">${{esc(r.source)}}</span>` : '');
}}

function render() {{
  const t = q.value.trim().toLowerCase(), k = fk.value, c = fc.value;
  const hit = DATA.filter(r =>
    (!k || r.kind === k) && (!c || r['出現ケース'].includes(c)) &&
    (!t || (r.author + r.title + r.source + r.context).toLowerCase().includes(t)));
  count.textContent = `${{hit.length}} 件を表示中（全 ${{DATA.length}} 件）`;
  list.innerHTML = hit.length ? hit.map(r => `
    <div class="item">
      <div class="cite">${{cite(r)}}</div>
      <div class="meta">
        <span class="chip ${{r.kind === CV ? 'cv' : ''}}">${{esc(r.kind)}}</span>
        ${{r['出現回数'] > 1 ? `<span>${{r['出現回数']}}回 引用</span>` : ''}}
        <a href="${{r.case_url}}" target="_blank" rel="noopener">${{esc(r.case_title)}}</a>
        ${{r.pdf ? `<a href="${{r.pdf}}" target="_blank" rel="noopener">${{esc(r.doc_name)}} (PDF)</a>`
                : `<span>${{esc(r.doc_name)}}</span>`}}
      </div>
      <details><summary>引用箇所の前後を見る</summary>
        <div class="ctx">${{esc(r.context)}}</div></details>
    </div>`).join('')
    : '<p class="empty">条件に合う文献がありません。</p>';
}}
[q, fk, fc].forEach(e => e.addEventListener('input', render));
render();
</script>
</body>
</html>
"""
out = os.path.join(DOCS, "index.html")
open(out, "w").write(HTML_DOC)
print(f"{out} を書き出した（{os.path.getsize(out)/1024:.0f}KB / {len(rows)}件）")
