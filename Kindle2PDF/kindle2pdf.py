#!/usr/bin/env python3
"""
kindle2pdf.py — Mac の Kindle アプリの画面を、1ページずつ自動で撮影して、1つの PDF にまとめます。

【ご注意】
 ・ご自身が購入した本を、ご自身のために使う（個人利用）目的に限ってください。
   できあがった PDF を、他人に渡したり、公開したりしないでください。
 ・Kindle の利用規約や、各国の著作権法で、制限されている場合があります。ご自身の責任でご利用ください。
 ・Kindle アプリによっては、スクリーンショットが真っ黒になる本があります。その場合は、撮影できません。

【使い方（Terminal）】
  python3 kindle2pdf.py --name 本の名前 --pages 5          # まず5ページで試す
  python3 kindle2pdf.py --name 本の名前 --pages 30 --direction left   # 日本語の縦書きの本は left

【事前の準備】
 ・Terminal に「画面収録」と「アクセシビリティ」の許可を与える
   （システム設定 → プライバシーとセキュリティ）。許可を変えたら Terminal を一度終了して開き直す。
 ・Kindle アプリで、本を開き、撮り始めたいページを表示しておく。
 ・Pillow が必要:  python3 -m pip install pillow
"""
import argparse
import hashlib
import subprocess
import sys
import time
from pathlib import Path

KEYCODES = {"left": 123, "right": 124}


def osascript(script: str) -> str:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "osascript に失敗しました")
    return r.stdout.strip()


def activate(app: str) -> None:
    # アプリ名で activate すると、別アプリ（Kindle Classic など）が起動することがあるため、
    # 動作中のプロセスを System Events で最前面にする
    osascript(
        f'tell application "System Events" to set frontmost of process "{app}" to true'
    )


def window_rect(app: str):
    out = osascript(
        f'tell application "System Events" to tell process "{app}" '
        f'to get {{position, size}} of window 1'
    )
    nums = [int(float(v)) for v in out.replace("{", "").replace("}", "").split(",")]
    if len(nums) != 4:
        raise RuntimeError(f"ウィンドウの位置を読み取れませんでした: {out}")
    return nums  # x, y, w, h


def capture(rect, path: Path, trim_top: int, trim_bottom: int) -> None:
    x, y, w, h = rect
    y += trim_top
    h -= trim_top + trim_bottom
    if w <= 0 or h <= 0:
        raise RuntimeError("撮影する範囲が、0 以下になりました（--trim の値を小さくしてください）。")
    r = subprocess.run(
        ["screencapture", "-x", "-R", f"{x},{y},{w},{h}", str(path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not path.exists():
        raise RuntimeError("撮影に失敗しました（Terminal の「画面収録」の許可を確認してください）。")


def turn_page(app: str, direction: str) -> None:
    activate(app)
    osascript(f'tell application "System Events" to key code {KEYCODES[direction]}')


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_pdf(images, pdf_path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        sys.exit("Pillow が必要です。  python3 -m pip install pillow  を実行してください。")
    pages = [Image.open(p).convert("RGB") for p in images]
    pages[0].save(pdf_path, save_all=True, append_images=pages[1:], resolution=144.0)


def main() -> None:
    ap = argparse.ArgumentParser(description="Kindle の画面を撮影して PDF にします")
    ap.add_argument("--name", required=True, help="本の名前（フォルダ名と PDF 名になります）")
    ap.add_argument("--pages", type=int, default=5, help="撮影するページ数（初期値 5）")
    ap.add_argument("--direction", choices=["left", "right"], default="right",
                    help="ページをめくる矢印キー。横書きは right、日本語の縦書きは left")
    ap.add_argument("--delay", type=float, default=1.5, help="めくったあと待つ秒数（初期値 1.5）")
    ap.add_argument("--start-delay", type=int, default=5, help="開始までの待ち時間の秒数（初期値 5）")
    ap.add_argument("--app", default="Kindle", help="アプリ名（初期値 Kindle）")
    ap.add_argument("--trim-top", type=int, default=0, help="ウィンドウの上から除く高さ（ポイント）")
    ap.add_argument("--trim-bottom", type=int, default=0, help="ウィンドウの下から除く高さ（ポイント）")
    ap.add_argument("--out", default=str(Path.home() / "Documents" / "KindleCapture"),
                    help="保存先の親フォルダ")
    ap.add_argument("--no-open", action="store_true", help="終了後に保存先フォルダを開かない")
    args = ap.parse_args()

    folder = Path(args.out).expanduser() / args.name
    folder.mkdir(parents=True, exist_ok=True)

    print(f"{args.start_delay} 秒後に開始します。Kindle を、撮り始めたいページにしておいてください。")
    print("止めたいときは、Terminal で control + C を押します。")
    for s in range(args.start_delay, 0, -1):
        print(f"  {s}…", end="\r", flush=True)
        time.sleep(1)

    activate(args.app)
    time.sleep(1)
    rect = window_rect(args.app)
    print(f"撮影する範囲: 位置({rect[0]},{rect[1]}) 大きさ({rect[2]}x{rect[3]})")

    images = []
    last = None
    same_count = 0
    for n in range(1, args.pages + 1):
        path = folder / f"page_{n:04d}.png"
        capture(rect, path, args.trim_top, args.trim_bottom)
        d = digest(path)
        if d == last:
            same_count += 1
            path.unlink()
            if same_count >= 2:
                print("同じ画面が続いたので、最後のページとみなして終了します。")
                break
        else:
            same_count = 0
            images.append(path)
            print(f"撮影 {len(images)} 枚目 ({path.name})")
        last = d
        if n < args.pages:
            turn_page(args.app, args.direction)
            time.sleep(args.delay)

    if not images:
        sys.exit("1枚も撮影できませんでした。")

    pdf_path = folder.parent / f"{args.name}.pdf"
    build_pdf(images, pdf_path)
    print(f"\nできました: {pdf_path}（{len(images)} ページ）")
    print(f"撮影した画像: {folder}")
    if not args.no_open:
        # Finder で PDF を選択した状態で保存先フォルダを開く
        subprocess.run(["open", "-R", str(pdf_path)])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n中断しました。")
    except RuntimeError as e:
        sys.exit(f"エラー: {e}")
