#!/usr/bin/env python3
"""縦書き・横書きが混在する日本語PDFをOCRして、ページ番号付きテキストにする。

ページごとに「縦書き」「横書き」を両方試し、確信度の高い方を採用する。
確信度が85未満のページは、縦書き+ページ構造の自動判定でも読み直す。
処理は中断しても、同じコマンドで続きから再開できる。

使い方:
  python3 -I ocr_vertical_jp.py ~/Desktop/book.pdf --book 本の名前
  -> 次の置き場に自動で整理される(--book を省くとPDFのファイル名が本の名前になる)。
       ~/Documents/書籍分析/<本の名前>/
         01_原本/      元のPDF(デスクトップ等から移動する。--copy ならコピー)
         02_OCR結果/   <名前>_ocr.txt(ページ番号 [p.N] 付き)と <名前>_ocr.pdf(検索可能PDF)
         99_作業用/    途中ファイル(不要になったら消してよい)
  途中で止まっても、同じコマンドで続きから再開できる。
  置き場を使わず、出力先を自分で決めるときは --out 出力名 を付ける。

準備(Macの場合):
  brew install tesseract poppler
  tessdata フォルダに jpn / jpn_vert / eng / osd の各 traineddata と、
  システムの configs フォルダ、pdf.ttf を置き、--tessdata で指定する(README参照)。
"""
import argparse, os, re, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor


def conf_of(tsv):
    num = den = 0
    for line in open(tsv, encoding="utf-8").read().splitlines()[1:]:
        c = line.split("\t")
        if len(c) >= 12 and c[11].strip() and float(c[10]) >= 0:
            w = len(c[11].strip())
            num += float(c[10]) * w
            den += w
    return (num / den if den else 0.0), den


def tesseract(png, out, lang, psm, env):
    for ext in ("txt", "tsv", "pdf"):
        if os.path.exists(f"{out}.{ext}"):
            os.remove(f"{out}.{ext}")
    subprocess.run(["tesseract", png, out + "_t", "-l", lang, "--psm", psm, "txt", "tsv", "pdf"],
                   env=env, capture_output=True)
    for ext in ("txt", "tsv", "pdf"):
        os.replace(f"{out}_t.{ext}", f"{out}.{ext}")  # 完成したものだけを残す(再開のため)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--book", default=None, help="本の名前(= ワークスペース名)。省略するとPDFのファイル名")
    ap.add_argument("--library", default=os.path.expanduser("~/Documents/書籍分析"),
                    help="本の置き場(既定: ~/Documents/書籍分析)")
    ap.add_argument("--copy", action="store_true", help="原本を移さず、コピーを置く")
    ap.add_argument("--out", default=None, help="出力名(拡張子なし)。指定すると置き場の自動整理は行わない")
    ap.add_argument("--workdir", default=None, help="途中経過の置き場(--out指定時のみ。既定: <out>_work)")
    ap.add_argument("--tessdata", default=os.path.expanduser("~/tessdata"))
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--pages", default=None, help="例: 10-12(省略すると全ページ)")
    a = ap.parse_args()

    a.pdf = os.path.abspath(os.path.expanduser(a.pdf))
    if a.out is None:
        # 置き場ルール: <library>/<本の名前>/{01_原本, 02_OCR結果, 99_作業用}
        stem = os.path.splitext(os.path.basename(a.pdf))[0]
        book_dir = os.path.join(a.library, a.book or stem)
        orig_dir = os.path.join(book_dir, "01_原本")
        res_dir = os.path.join(book_dir, "02_OCR結果")
        work = os.path.join(book_dir, "99_作業用")
        for d in (orig_dir, res_dir, work):
            os.makedirs(d, exist_ok=True)
        dest = os.path.join(orig_dir, os.path.basename(a.pdf))
        if os.path.exists(a.pdf) and os.path.abspath(a.pdf) != os.path.abspath(dest):
            if os.path.exists(dest):
                sys.exit(f"原本の置き場に同名のファイルがあります: {dest}")
            (shutil.copy2 if a.copy else shutil.move)(a.pdf, dest)  # 移動(--copy ならコピー)
            print(f"原本を {'コピー' if a.copy else '移動'}: {dest}")
        elif not os.path.exists(a.pdf) and not os.path.exists(dest):
            sys.exit(f"PDFが見つかりません: {a.pdf}")
        a.pdf = dest
        a.out = os.path.join(res_dir, stem + "_ocr")
    else:
        work = a.workdir or a.out + "_work"
    os.makedirs(work, exist_ok=True)
    env = dict(os.environ, TESSDATA_PREFIX=a.tessdata, OMP_THREAD_LIMIT="1")
    total = int(re.search(r"Pages:\s+(\d+)", subprocess.run(
        ["pdfinfo", a.pdf], capture_output=True, text=True).stdout).group(1))
    first, last = (1, total)
    if a.pages:
        first, last = map(int, a.pages.split("-"))
    pages = list(range(first, last + 1))

    def run(p):
        base = f"{work}/p{p:03d}"
        if not os.path.exists(base + ".png"):
            subprocess.run(["pdftoppm", "-r", str(a.dpi), "-f", str(p), "-l", str(p), "-gray", "-png",
                            "-singlefile", a.pdf, base + "_t"], check=True)
            os.replace(base + "_t.png", base + ".png")
        res = {}
        for tag, lang, psm in (("v", "jpn_vert", "5"), ("h", "jpn+eng", "3")):
            if not os.path.exists(f"{base}_{tag}.pdf"):
                tesseract(base + ".png", f"{base}_{tag}", lang, psm, env)
            res[tag] = conf_of(f"{base}_{tag}.tsv")
        if max(res["v"][0], res["h"][0]) < 85:
            if not os.path.exists(f"{base}_w.pdf"):
                tesseract(base + ".png", f"{base}_w", "jpn_vert", "3", env)
            res["w"] = conf_of(f"{base}_w.tsv")
        pick = max(res, key=lambda k: res[k][0])
        print(f"p{p:03d} " + " ".join(f"{k}={v[0]:.0f}" for k, v in res.items()) + f" -> {pick}", flush=True)
        return p, pick, res[pick][0]

    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        results = list(ex.map(run, pages))
    picks = {p: k for p, k, _ in results}

    with open(a.out + ".txt", "w", encoding="utf-8") as f:
        for p in pages:
            t = open(f"{work}/p{p:03d}_{picks[p]}.txt", encoding="utf-8").read()
            # 日本語文字の間に入る余計な空白を取る
            t = re.sub(r"(?<=[　-鿿＀-￯]) (?=[　-鿿＀-￯])", "", t)
            f.write(f"\n\n[p.{p}]\n{t.strip()}\n")
    subprocess.run(["pdfunite"] + [f"{work}/p{p:03d}_{picks[p]}.pdf" for p in pages] + [a.out + ".pdf"],
                   check=True)
    low = [(p, round(c)) for p, _, c in results if c < 80]
    print(f"完了: {len(pages)}ページ。確信度80未満のページ(要確認): {low}")


if __name__ == "__main__":
    sys.exit(main())
