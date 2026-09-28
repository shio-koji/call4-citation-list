#!/usr/bin/env python3
"""抽出した引用文献を、誰にでも見せられる公開サイトにする。

全96ケース規模だと件数が数千になるので、
  - データは docs/data.json に外出しして読み込む（HTMLを軽く保つ）
  - 一覧は100件ずつ描画する（数千件を一度にDOMに入れない）
の2点で重さを避けている。出力先は docs/（GitHub Pages の main/docs 設定で公開）。
"""
import json, os, re, html, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs"); os.makedirs(DOCS, exist_ok=True)
CV = "執筆者の業績（引用ではない）"
CASE_URL = "https://www.call4.jp/info.php?type=items&id="

rows = json.load(open(os.path.join(HERE, "out_citations.json")))
survey = {r["id"]: r for r in json.load(open(os.path.join(HERE, "out_survey.json")))}
cases_all = {c["id"]: c for c in
             json.load(open(os.path.join(HERE, "cache", "cases_list.json")))["cases"]}

for r in rows:
    r["context"] = r["context"][:170]

real = [r for r in rows if r["kind"] != CV]
kinds = collections.Counter(r["kind"] for r in rows)

# ケースごとの引用件数
bycase = collections.Counter()
for r in real:
    for c in r["出現ケース"]:
        bycase[c] += 1
seen_cases = sorted(bycase, key=lambda c: -bycase[c])
n_doc_read = len({r["doc"] for r in rows})
n_doc_all = sum(s["n"] for s in survey.values())

# 複数のケースにまたがって引用されている文献＝分野を越えて参照されている定番
cross = sorted([r for r in real if len(r["出現ケース"]) > 1],
               key=lambda r: (-len(r["出現ケース"]), -r["出現回数"]))[:20]

TILES = [("対象ケース", len(cases_all), "件"),
         ("読み込んだ訴訟資料", n_doc_all, "件"),
         ("抽出した学術文献", len(real), "件"),
         ("うち論文（雑誌掲載）", kinds.get("論文（雑誌掲載）", 0), "件")]


def cite_text(r):
    o, c = ("「", "」") if r.get("bracket") == "「" else \
           ("『", "』") if r.get("bracket") else ("", "")
    a = f"{r['author']} " if r["author"] else ""
    s = f" {r['source']}" if r["source"] else ""
    return f"{a}{o}{r['title']}{c}{s}"


tiles_html = "\n".join(
    f'<div class="tile"><div class="tile-n">{v:,}<span class="tile-u">{u}</span></div>'
    f'<div class="tile-l">{html.escape(l)}</div></div>' for l, v, u in TILES)

cross_html = "\n".join(
    f'<li><span class="cx-n">{len(r["出現ケース"])}<span class="cx-u">ケース</span></span>'
    f'<span class="cx-t">{html.escape(cite_text(r))}</span></li>' for r in cross)

rank_html = "\n".join(
    f'<li><a href="#" data-case="{c}">{html.escape(cases_all[c]["title"])}</a>'
    f'<span class="cs">資料{survey[c]["n"]}件 · 引用{bycase[c]}件</span></li>'
    for c in seen_cases)

case_opts = "\n".join(
    f'<option value="{c}">{html.escape(cases_all[c]["title"])[:40]}（{bycase[c]}）</option>'
    for c in seen_cases)
kind_opts = "\n".join(
    f'<option value="{html.escape(k)}">{html.escape(k)}（{n}）</option>'
    for k, n in kinds.most_common())

# 一覧用のデータは必要な項目だけに絞って外出しする
slim = [{"a": r["author"], "t": r["title"], "s": r["source"], "b": r.get("bracket", ""),
         "k": r["kind"], "n": r["出現回数"], "cs": r["出現ケース"],
         "ct": r["case_title"], "cu": CASE_URL + r["case"],
         "dn": r["doc_name"], "p": r.get("pdf", ""), "x": r["context"]} for r in rows]
json.dump(slim, open(os.path.join(DOCS, "data.json"), "w"),
          ensure_ascii=False, separators=(",", ":"))

HTML_DOC = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CALL4 訴訟資料の引用文献リスト</title>
<meta name="description" content="CALL4に公開されている公共訴訟{len(cases_all)}件の訴訟資料が引用している学術文献を抽出したリスト。">
<style>
:root {{
  color-scheme: light dark;
  --surface:#fcfcfb; --card:#ffffff; --line:#e7e6e2;
  --ink:#0b0b0b; --ink2:#52514e; --ink3:#8a8981;
  --accent:#2a78d6; --accent-soft:#eaf2fd; --warn-bg:#fdf6e6; --warn-line:#eda100;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --surface:#1a1a19; --card:#232321; --line:#333330;
    --ink:#ffffff; --ink2:#c3c2b7; --ink3:#8a8981;
    --accent:#3987e5; --accent-soft:#1d2a3b; --warn-bg:#2b2517; --warn-line:#c98500;
  }}
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--surface); color:var(--ink); font-size:15px; line-height:1.75;
  font-family:"Hiragino Sans","Yu Gothic",system-ui,sans-serif; }}
.wrap {{ max-width:1120px; margin:0 auto; padding:40px 20px 80px; }}
h1 {{ font-size:25px; margin:0 0 6px; }}
h2 {{ font-size:13px; font-weight:600; color:var(--ink3); margin:0 0 10px; letter-spacing:.04em; }}
.sub {{ color:var(--ink2); margin:0 0 24px; }}
a {{ color:var(--accent); }}
.note {{ background:var(--warn-bg); border-left:3px solid var(--warn-line); padding:14px 18px;
  border-radius:0 6px 6px 0; margin:0 0 28px; color:var(--ink2); font-size:14px; }}
.note b {{ color:var(--ink); }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin:0 0 34px; }}
.tile {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:16px 18px; }}
.tile-n {{ font-size:30px; font-weight:650; line-height:1.2; }}
.tile-u {{ font-size:14px; font-weight:400; color:var(--ink2); margin-left:3px; }}
.tile-l {{ font-size:13px; color:var(--ink2); margin-top:2px; }}
section {{ margin:0 0 34px; }}
.cross {{ margin:0; padding:0; list-style:none; }}
.cross li {{ display:flex; gap:12px; align-items:baseline; padding:7px 0;
  border-bottom:1px solid var(--line); font-size:14.5px; }}
.cross li:last-child {{ border-bottom:0; }}
.cx-n {{ flex:0 0 66px; color:var(--accent); font-weight:650; font-variant-numeric:tabular-nums; }}
.cx-u {{ font-size:11.5px; font-weight:400; color:var(--ink3); margin-left:2px; }}
details.cases > summary {{ cursor:pointer; color:var(--ink3); font-size:13px;
  font-weight:600; letter-spacing:.04em; }}
.cases ol {{ margin:10px 0 0; padding:0; list-style:none; counter-reset:c;
  max-height:420px; overflow:auto; }}
.cases li {{ counter-increment:c; display:flex; flex-wrap:wrap; align-items:baseline; gap:4px 10px;
  padding:6px 0 6px 30px; position:relative; border-bottom:1px solid var(--line); font-size:14px; }}
.cases li::before {{ content:counter(c); position:absolute; left:0; top:6px; color:var(--ink3);
  font-size:12px; font-variant-numeric:tabular-nums; }}
.cases .cs {{ color:var(--ink3); font-size:12.5px; }}
.controls {{ display:flex; flex-wrap:wrap; gap:10px; margin:0 0 6px; }}
input[type=search], select {{ font:inherit; font-size:14px; padding:9px 12px; color:var(--ink);
  background:var(--card); border:1px solid var(--line); border-radius:7px; }}
input[type=search] {{ flex:1 1 280px; }}
.count {{ color:var(--ink3); font-size:13px; margin:0 0 14px; }}
.item {{ border-bottom:1px solid var(--line); padding:15px 2px; }}
.cite {{ font-size:15.5px; }}
.cite .au {{ font-weight:600; }}
.cite .so {{ color:var(--ink2); }}
.meta {{ margin-top:5px; font-size:12.5px; color:var(--ink3); display:flex; flex-wrap:wrap;
  gap:6px 12px; align-items:center; }}
.chip {{ display:inline-block; padding:1px 9px; border-radius:999px; font-size:11.5px;
  background:var(--accent-soft); color:var(--accent); }}
.chip.cv {{ background:transparent; border:1px solid var(--line); color:var(--ink3); }}
details.ctx-d {{ margin-top:7px; }}
details.ctx-d > summary {{ cursor:pointer; color:var(--ink3); font-size:12.5px; }}
.ctx {{ margin-top:7px; padding:11px 14px; background:var(--card); border:1px solid var(--line);
  border-radius:6px; font-size:13px; color:var(--ink2); line-height:1.85; }}
.more {{ display:block; width:100%; margin:20px 0 0; padding:12px; font:inherit; font-size:14px;
  cursor:pointer; color:var(--ink); background:var(--card);
  border:1px solid var(--line); border-radius:7px; }}
.empty {{ padding:50px 0; text-align:center; color:var(--ink3); }}
footer {{ margin-top:46px; padding-top:22px; border-top:1px solid var(--line);
  font-size:13px; color:var(--ink3); }}
footer a {{ color:var(--ink2); }}
</style>
</head>
<body>
<div class="wrap">

<h1>CALL4 訴訟資料の引用文献リスト</h1>
<p class="sub">公共訴訟プラットフォーム <a href="https://www.call4.jp/">CALL4</a> に公開されている
<b>{len(cases_all)}件すべての訴訟</b>について、その訴訟資料がどんな学術文献を引用しているかを機械的に抽出したものです。</p>

<div class="note">
<b>自動抽出の結果です。</b> 人手による確認を経ていないため、誤って拾ったもの・取りこぼしたものが含まれます。
とくに <code>前掲注(24)</code> のような2回目以降の省略引用は拾えていません。
引用の正確な内容は、かならず出典元の資料そのものをご確認ください。
</div>

<div class="tiles">{tiles_html}</div>

<section>
<h2>分野を越えて引用されている文献</h2>
<p class="sub" style="margin-bottom:12px;font-size:13.5px">複数の訴訟で引用された文献です。件数はケース数。</p>
<ol class="cross">{cross_html}</ol>
</section>

<section>
<details class="cases">
<summary>ケース別の引用件数（{len(seen_cases)}件。クリックで開く）</summary>
<ol>{rank_html}</ol>
</details>
</section>

<section>
<h2>すべての文献</h2>
<div class="controls">
  <input type="search" id="q" placeholder="著者名・書名・雑誌名で絞り込む（例: 芦部、憲法、ジュリスト）">
  <select id="kind"><option value="">すべての種類</option>{kind_opts}</select>
  <select id="case"><option value="">すべてのケース</option>{case_opts}</select>
</div>
<p class="count" id="count">読み込み中…</p>
<div id="list"></div>
<button class="more" id="more" hidden>もっと見る</button>
</section>

<footer>
<p><b>作り方</b> — CALL4のAPIで訴訟資料{n_doc_all:,}件の本文を取得し、
「著者『書名』(出版社、年)頁」という書式のうち、鉤括弧の直後に書誌情報が続くものを引用として抽出しています。
訴訟書面の自己参照（<code>準備書面12頁</code>）、判例（<code>民集59巻7号2087頁</code>）、
証拠番号（<code>甲15・3頁</code>）は除外しました。判例の抽出は対象外です。</p>
<p><b>「執筆者の業績」とは</b> — 意見書の末尾には執筆者自身の経歴と主要著作が載っています。
これは訴訟で引用された文献ではないので、種類を分けてあります。</p>
<p><b>データの出どころ</b> — すべて <a href="https://www.call4.jp/">CALL4</a> の公開データです。
訴訟資料の権利はCALL4および各ケースの関係者にあります。
引用箇所の前後の文章は、どの文献を指しているかを確認できるようにするための短い抜粋です。</p>
<p><a href="https://github.com/shio-koji/call4-citation-list">ソースコードと抽出手順（GitHub）</a></p>
</footer>

</div>
<script>
const CV = '執筆者の業績（引用ではない）', PAGE = 100;
const q = document.getElementById('q'), fk = document.getElementById('kind'),
      fc = document.getElementById('case'), list = document.getElementById('list'),
      count = document.getElementById('count'), more = document.getElementById('more');
let DATA = [], hit = [], shown = 0;
const esc = s => (s||'').replace(/[&<>"]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));

function cite(r) {{
  const o = r.b === '「' ? '「' : (r.b ? '『' : ''), c = r.b === '「' ? '」' : (r.b ? '』' : '');
  return (r.a ? `<span class="au">${{esc(r.a)}}</span> ` : '')
       + `${{o}}${{esc(r.t)}}${{c}}`
       + (r.s ? ` <span class="so">${{esc(r.s)}}</span>` : '');
}}
const card = r => `
  <div class="item">
    <div class="cite">${{cite(r)}}</div>
    <div class="meta">
      <span class="chip ${{r.k === CV ? 'cv' : ''}}">${{esc(r.k)}}</span>
      ${{r.n > 1 ? `<span>${{r.n}}回 引用</span>` : ''}}
      ${{r.cs.length > 1 ? `<span>${{r.cs.length}}ケースで引用</span>` : ''}}
      <a href="${{r.cu}}" target="_blank" rel="noopener">${{esc(r.ct)}}</a>
      ${{r.p ? `<a href="${{r.p}}" target="_blank" rel="noopener">${{esc(r.dn)}} (PDF)</a>`
             : `<span>${{esc(r.dn)}}</span>`}}
    </div>
    <details class="ctx-d"><summary>引用箇所の前後を見る</summary>
      <div class="ctx">${{esc(r.x)}}</div></details>
  </div>`;

function draw(reset) {{
  if (reset) {{ list.innerHTML = ''; shown = 0; }}
  const next = hit.slice(shown, shown + PAGE);
  list.insertAdjacentHTML('beforeend', next.map(card).join(''));
  shown += next.length;
  more.hidden = shown >= hit.length;
  more.textContent = `もっと見る（残り ${{(hit.length - shown).toLocaleString()}} 件）`;
  count.textContent = `${{hit.length.toLocaleString()}} 件中 ${{shown.toLocaleString()}} 件を表示`
                    + `（全 ${{DATA.length.toLocaleString()}} 件）`;
}}
function filter() {{
  const t = q.value.trim().toLowerCase(), k = fk.value, c = fc.value;
  hit = DATA.filter(r => (!k || r.k === k) && (!c || r.cs.includes(c)) &&
    (!t || (r.a + r.t + r.s + r.x).toLowerCase().includes(t)));
  if (!hit.length) {{
    list.innerHTML = '<p class="empty">条件に合う文献がありません。</p>';
    more.hidden = true; shown = 0;
    count.textContent = `0 件（全 ${{DATA.length.toLocaleString()}} 件）`;
    return;
  }}
  draw(true);
}}
[q, fk, fc].forEach(e => e.addEventListener('input', filter));
more.addEventListener('click', () => draw(false));
document.querySelectorAll('[data-case]').forEach(a => a.addEventListener('click', e => {{
  e.preventDefault(); fc.value = a.dataset.case; filter();
  document.getElementById('q').scrollIntoView({{behavior:'smooth', block:'center'}});
}}));

fetch('data.json').then(r => r.json()).then(d => {{ DATA = d; filter(); }})
  .catch(() => count.textContent = 'データの読み込みに失敗しました。');
</script>
</body>
</html>
"""
open(os.path.join(DOCS, "index.html"), "w").write(HTML_DOC)
print(f"docs/index.html {os.path.getsize(os.path.join(DOCS,'index.html'))/1024:.0f}KB / "
      f"docs/data.json {os.path.getsize(os.path.join(DOCS,'data.json'))/1024:.0f}KB "
      f"({len(rows)}件, {len(cases_all)}ケース)")
