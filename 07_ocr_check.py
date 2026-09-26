#!/usr/bin/env python3
"""APIが本文を返さなかった資料を、手元でOCRして救えるか確かめる。

流れ: PDFをダウンロード（06で取得済みならそれを使う）
      → 暗号化されていれば空パスワードで解除 → pdftoppm で画像化
      → macOS標準のOCR(Vision) にかける

必要なもの: pypdf / pdftoppm(poppler) / swiftc。いずれも追加インストール不要な環境で確認済み。
使い方: python3 07_ocr_check.py <資料ID> [ページ範囲 例 10-11]
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work"); os.makedirs(WORK, exist_ok=True)
BIN = os.path.join(WORK, "ocr_vision")

doc_id = sys.argv[1] if len(sys.argv) > 1 else "003434"
rng = sys.argv[2] if len(sys.argv) > 2 else "10-11"
first, last = (int(x) for x in rng.split("-"))

src = os.path.join(HERE, "cache", "pdf", f"{doc_id}.pdf")
if not os.path.exists(src):
    sys.exit(f"{src} が無い。先に 06_probe_failed_pdfs.py でダウンロードすること")

import pypdf
rd = pypdf.PdfReader(src)
if rd.is_encrypted:
    ok = rd.decrypt("")        # 閲覧制限ではなく編集制限なら空パスワードで解除できる
    print(f"暗号化されていたので解除した（成功: {bool(ok)}）")
w = pypdf.PdfWriter()
for pg in rd.pages[first - 1:last]:
    w.add_page(pg)
dec = os.path.join(WORK, f"{doc_id}_p{first}-{last}.pdf")
w.write(dec)
print(f"{last-first+1}ページを切り出した: {dec}")

stem = os.path.join(WORK, f"{doc_id}_pg")
subprocess.run(["pdftoppm", "-r", "200", "-png", dec, stem], check=True)
pngs = sorted(f for f in os.listdir(WORK)
              if f.startswith(os.path.basename(stem)) and f.endswith(".png"))
print(f"画像化: {len(pngs)}枚")

if not os.path.exists(BIN):
    subprocess.run(["swiftc", "-O", os.path.join(HERE, "ocr_vision.swift"), "-o", BIN], check=True)
    print("OCRプログラムをビルドした")

subprocess.run([BIN] + [os.path.join(WORK, p) for p in pngs], check=True)
