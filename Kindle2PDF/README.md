# Kindle2PDF

Mac の Kindle アプリの画面を、1ページずつ自動で撮影して、1つの PDF にまとめるスクリプトです（offline-pdf の仲間のツール）。

## 使い方

```
cd ~/offline-pdf/Kindle2PDF
python3 kindle2pdf.py --name 本の名前 --pages 5                  # まず5ページで試す
python3 kindle2pdf.py --name 本の名前 --pages 30 --direction left   # 日本語の縦書きの本は left
```

- 保存先: `~/Documents/KindleCapture/本の名前/`（画像）と `~/Documents/KindleCapture/本の名前.pdf`
- 事前の準備: Terminal に「画面収録」「アクセシビリティ」の許可を与える／`python3 -m pip install pillow`
- 同じ画面が2回続くと、最後のページとみなして止まります。

## 注意

ご自身が購入した本を、ご自身のために使う範囲にとどめてください。PDF を他人に渡したり、公開したりしないでください。Kindle の利用規約や著作権法で制限されることがあります。本によっては、スクリーンショットが真っ黒になります。

## アプリ版（ダブルクリックで使う）

`KindleCapture.applescript` から、かんたんなアプリ「Kindle撮影PDF」を作れます。

```
osacompile -o ~/Applications/Kindle撮影PDF.app ~/offline-pdf/Kindle2PDF/KindleCapture.applescript
```

撮影そのものは Terminal が行うので、Terminal に画面収録とアクセシビリティを許可していれば、このアプリには許可の設定は不要です。
