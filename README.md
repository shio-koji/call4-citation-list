# CALL4 訴訟資料 引用論文リスト

**公開ページ（試作）**: https://shio-koji.github.io/call4-citation-list/

**次にやること** — 省略引用（`前掲注(24)`）の解決、判例の抽出、証拠提出された論文の抽出、全96ケースへの展開。

## 分かっていること（要点）

| | |
|---|---|
| 公開ケース | 96件 |
| 訴訟資料 | 7,090件（書面4,819 / 証拠1,956 / 判決315） |
| うちテキスト化済み | 6,825件（96.3%） |
| APIドキュメントの50,000文字上限 | **実際には掛かっていない**（実測最長 373,189文字） |
| PDFそのもの | APIでは取れないが、サイトのHTMLから全件取れる（資料IDとの対応づけ99.6%） |
| PDFの中身 | 多くが画像スキャン。**APIのテキストはCALL4側でOCR済み**で、自前処理より質が高い |
| `has_text` フラグ | `True`は100%信用できる。`False`でも22%は本文が取れる |
| 取れない資料 | 手元でOCRすれば救えるものがある（実証済み）。ただし0バイトのファイルと動画(.mp4)は救えない |
| 引用抽出 | **できる。** 4ケース・資料133件から学術文献201件（書籍129/論文64/英語8）を抽出した |

## スクリプト

番号順に実行する。いずれも `cache/` にキャッシュするので、再実行時は取得し直さない。

| | 何をするか | 出力 |
|---|---|---|
| `01_survey_documents.py` | 全96ケースの資料を棚卸しする | `out_survey.json` |
| `02_verify_text.py` | `has_text` フラグが本当か、269件を実取得して検証 | `out_verify.json` |
| `03_report_survey.py` | 棚卸し結果を読み物とCSVにする | 中間報告01, `out_ケース別_資料数.csv` |
| `04_report_api.py` | API仕様の実測結果を読み物にする | 中間報告02, `out_テキスト検証_サンプル269件.csv` |
| `05_plot_lengths.py` | 本文の長さのヒストグラムを描く | `fig_本文の長さ_{light,dark}.png` |
| `06_probe_failed_pdfs.py` | 本文が取れない資料のPDFを落として素性を調べる | `out_failed_pdfs.json` |
| `07_ocr_check.py` | そのPDFを手元でOCRできるか試す（`ocr_vision.swift` を使う） | 標準出力 |
| `08_fetch_case_texts.py` | 試作対象4ケースの本文をすべて取る | `cache/text/` |
| `09_extract_citations.py` | 本文から引用文献を抽出する | `out_引用文献_候補.csv` |
| `10_report_citations.py` | 抽出結果を読み物にする | 中間報告03 |
| `11_build_site.py` | 共有用の1枚HTMLを組み立てる | `docs/index.html` |

**必要なもの** — Python（`pypdf`）、`pdftoppm`（poppler）、`swiftc`。追加インストール無しで動く環境で確認済み。

## データの置き場所

`cache/` は**バージョン管理していない**（PDFだけで320MBあり、スクリプトで再生成できるため）。

| | |
|---|---|
| `cache/cases_list.json` | 全ケース一覧 |
| `cache/docs_<ケースID>.json` | 資料一覧のAPI応答 |
| `cache/text/<資料ID>.json` | 本文のAPI応答 |
| `cache/matpage/<ケースID>.html` | 資料一覧ページのHTML（PDFリンクの取得元） |
| `cache/pdf/<資料ID>.pdf` | ダウンロードしたPDF |

## APIの叩き方

`POST https://www.call4.jp/flight_api/mcp/sse` に JSON-RPC 2.0。認証不要。
`Accept: application/json` を付けると素のJSONで返る。詳細は `~/.claude/skills/call4/SKILL.md`。

**落とし穴** — 応答は二重にJSONになっている（`result.content[0].text` を再度パースする）。
失敗はHTTP 500で返る。さらに `content[0].text` が文字列でなく `false` で返る資料があるので型チェックが要る。

## 公開ページ

`docs/index.html` を GitHub Pages（mainブランチの `/docs`）で配信している。
外部ファイルに依存しない自己完結HTMLなので、ファイル1つ渡すだけでも共有できる。
更新は `python3 11_build_site.py` で作り直してコミットするだけ。

## 扱いの注意

公開データだが、**ケース本文・資料の権利はCALL4と各ケースの関係者にある**。
公開ページには訴訟資料からの短い抜粋（引用箇所の前後）を載せているため、
**CALL4に一度見てもらい、必要なら表示を調整する前提**で扱う。

ページ冒頭には「試作版であること」「人手の確認を経ていないこと」
「省略引用を拾えていないこと」を明記してある。数字が独り歩きしないようにするため。
