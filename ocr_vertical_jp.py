#!/usr/bin/env python3
"""縦書き・横書きが混在する日本語PDFをOCRして、ページ番号付きテキストにする。

ページごとに「縦書き」「横書き」を両方試し、確信度の高い方を採用する。
確信度が85未満のページは、縦書き+ページ構造の自動判定でも読み直す。
処理は中断しても、同じコマンドで続きから再開できる。

使い方:
  python3 -I ocr_vertical_jp.py book.pdf --out book_ocr
  -> book_ocr.txt(ページ番号 [p.N] 付き)と book_ocr.pdf(検索可能PDF)ができる。

準備(Macの場合):
  brew install tesseract poppler
  tessdata フォルダに jpn / jpn_vert / eng / osd の各 traineddata と、
  システムの configs フォルダ、pdf.ttf を置き、--tessdata で指定する(README参照)。
"""
import argparse, os, re, subprocess, sys
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
    ap.add_argument("--out", required=True, help="出力名(拡張子なし)")
    ap.add_argument("--workdir", default=None, help="途中経過の置き場(既定: <out>_work)")
    ap.add_argument("--tessdata", default=os.path.expanduser("~/tessdata"))
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--pages", default=None, help="例: 10-12(省略すると全ページ)")
    a = ap.parse_args()

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
