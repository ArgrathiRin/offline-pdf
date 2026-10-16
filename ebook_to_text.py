#!/usr/bin/env python3
"""電子書籍(.azw3 / .azw / .mobi / .epub)を、章の見出し付きテキストにする。

OCRは不要(文字が最初からテキストのため、誤読は起きない)。
DRM(コピー防止)付きの本は変換できない。DRMなしのファイルだけを対象にする。

使い方:
  python3 -I ebook_to_text.py ~/Desktop/book.azw3 --book 本の名前
  -> 次の置き場に自動で整理される(--book を省くとファイル名が本の名前になる)。
       ~/Documents/書籍分析/<本の名前>/
         01_原本/      元のファイル(移動する。--copy ならコピー)
         02_テキスト/  <名前>.txt(章の見出し [章N: タイトル] 付き)
         99_作業用/    途中ファイル(epub。不要になったら消してよい)
  ページ番号は無いので、出典は章の見出しで示す。

準備(Macの場合):
  brew install --cask calibre      # ebook-convert を使う(.epub を直接渡すなら不要)
"""
import argparse, html, os, posixpath, re, shutil, subprocess, sys, zipfile
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

EBOOK_CONVERT_CANDIDATES = [
    "ebook-convert",
    "/Applications/calibre.app/Contents/MacOS/ebook-convert",
]
BLOCK = {"p", "div", "br", "li", "tr", "section", "article", "blockquote",
         "h1", "h2", "h3", "h4", "h5", "h6"}


class Extract(HTMLParser):
    """XHTMLから本文テキストを取り出す。ルビ(ふりがな)は本文だけ残す。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip, self.head, self.title = [], 0, None, ""
        self.first_head = ""

    def handle_starttag(self, tag, attrs):
        if tag in ("rt", "rp", "script", "style", "head"):
            self.skip += 1
        if tag in BLOCK:
            self.out.append("\n")
        if tag in ("h1", "h2", "h3") and not self.first_head:
            self.head = []

    def handle_endtag(self, tag):
        if tag in ("rt", "rp", "script", "style", "head"):
            self.skip = max(0, self.skip - 1)
        if tag in BLOCK:
            self.out.append("\n")
        if tag in ("h1", "h2", "h3") and self.head is not None:
            self.first_head = "".join(self.head).strip()
            self.head = None

    def handle_data(self, data):
        if self.skip:
            return
        self.out.append(data)
        if self.head is not None:
            self.head.append(data)


def clean(text):
    text = text.replace("　", "　")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"(?<=[　-鿿＀-￯]) (?=[　-鿿＀-￯])", "", text)  # 日本語の間の余計な空白
    lines = [l.strip() for l in text.split("\n")]
    out, blank = [], 0
    for l in lines:
        if l:
            out.append(l)
            blank = 0
        else:
            blank += 1
            if blank == 1:
                out.append("")
    return "\n".join(out).strip()


def epub_sections(path):
    """epubを読み順(spine)に並べて、[(見出し, 本文), ...] を返す。"""
    z = zipfile.ZipFile(path)
    container = ET.fromstring(z.read("META-INF/container.xml"))
    opf_path = container.find(".//{*}rootfile").get("full-path")
    opf = ET.fromstring(z.read(opf_path))
    base = posixpath.dirname(opf_path)
    manifest = {i.get("id"): i.get("href") for i in opf.findall(".//{*}manifest/{*}item")}
    sections = []
    for ref in opf.findall(".//{*}spine/{*}itemref"):
        href = manifest.get(ref.get("idref"))
        if not href:
            continue
        name = posixpath.normpath(posixpath.join(base, html.unescape(href).split("#")[0]))
        name = re.sub(r"%([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), name) \
            if name not in z.namelist() else name
        if name not in z.namelist():
            continue
        raw = z.read(name).decode("utf-8", errors="replace")
        ex = Extract()
        ex.feed(raw)
        body = clean("".join(ex.out))
        if len(body) >= 1:
            sections.append((ex.first_head, body))
    return sections


def find_convert():
    for c in EBOOK_CONVERT_CANDIDATES:
        if shutil.which(c) or os.path.exists(c):
            return shutil.which(c) or c
    return None


def to_epub(src, epub):
    exe = find_convert()
    if not exe:
        sys.exit("ebook-convert が見つかりません。brew install --cask calibre を実行してください。")
    r = subprocess.run([exe, src, epub], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(epub):
        msg = (r.stdout + r.stderr)
        if "DRM" in msg.upper():
            sys.exit("この本はDRM(コピー防止)付きのため変換できません。DRMなしのファイルだけが対象です。")
        sys.exit("変換に失敗しました:\n" + msg[-800:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ebook")
    ap.add_argument("--book", default=None, help="本の名前(= ワークスペース名)。省略するとファイル名")
    ap.add_argument("--library", default=os.path.expanduser("~/Documents/書籍分析"),
                    help="本の置き場(既定: ~/Documents/書籍分析)")
    ap.add_argument("--copy", action="store_true", help="原本を移さず、コピーを置く")
    a = ap.parse_args()

    src = os.path.abspath(os.path.expanduser(a.ebook))
    stem = os.path.splitext(os.path.basename(src))[0]
    book_dir = os.path.join(a.library, a.book or stem)
    orig_dir, res_dir, work = (os.path.join(book_dir, d) for d in ("01_原本", "02_テキスト", "99_作業用"))
    for d in (orig_dir, res_dir, work):
        os.makedirs(d, exist_ok=True)
    dest = os.path.join(orig_dir, os.path.basename(src))
    if os.path.exists(src) and src != dest:
        if os.path.exists(dest):
            sys.exit(f"原本の置き場に同名のファイルがあります: {dest}")
        (shutil.copy2 if a.copy else shutil.move)(src, dest)
        print(f"原本を {'コピー' if a.copy else '移動'}: {dest}")
    elif not os.path.exists(src) and not os.path.exists(dest):
        sys.exit(f"ファイルが見つかりません: {src}")

    if dest.lower().endswith(".epub"):
        epub = dest
    else:
        epub = os.path.join(work, stem + ".epub")
        if not os.path.exists(epub):
            to_epub(dest, epub)

    sections = epub_sections(epub)
    if not sections:
        sys.exit("本文を取り出せませんでした(画像だけの本の可能性があります。その場合はOCRが必要です)。")
    out = os.path.join(res_dir, stem + ".txt")
    total = 0
    with open(out + ".tmp", "w", encoding="utf-8") as f:
        for i, (title, body) in enumerate(sections, 1):
            f.write(f"\n\n[章{i}: {title or '(見出しなし)'}]\n{body}\n")
            total += len(body)
    os.replace(out + ".tmp", out)
    print(f"完了: {len(sections)}セクション、約{total:,}文字 -> {out}")
    short = [i for i, (_, b) in enumerate(sections, 1) if len(b) < 30]
    if short:
        print(f"本文がごく短いセクション(表紙・扉など): {short}")


if __name__ == "__main__":
    sys.exit(main())
