# Kindle2PDF ルーチン

Mac の Kindle アプリの画面を1ページずつ自動で撮影して、1つの PDF にまとめるツールの手順書です。ツールは GitHub の ArgrathiRin/offline-pdf の `Kindle2PDF/` フォルダにあります（Mac では `~/offline-pdf/Kindle2PDF`）。

**注意：** ご自身が購入した本を、ご自身のために使う範囲にとどめます。PDF を他人に渡したり公開したりしないでください。本によっては、スクリーンショットが真っ黒になります。

## 初回だけの準備

1. システム設定 → プライバシーとセキュリティ → 「画面収録」と「アクセシビリティ」で、Terminal をオンにします。そのあと Terminal を一度終了して、開き直します。
2. Pillow を入れます。通常のコマンドは「externally-managed-environment」で止まるので、次を使います。
   `python3 -m pip install --user --break-system-packages pillow`
3. アプリ「Kindle撮影PDF」を作ります（初回と、ファイルを更新したあとに実行します）。
   `rm -rf ~/Applications/Kindle撮影PDF.app && osacompile -o ~/Applications/Kindle撮影PDF.app ~/offline-pdf/Kindle2PDF/KindleCapture.applescript`
4. Kindle アプリの表示を白背景にします。「Aa」ボタン → 色（テーマ）→ 白。

## 使い方（アプリ版）

1. Kindle Classic が起動していたら終了し、新しい Kindle だけを開きます。
2. Kindle で、撮り始めたいページを表示します。
3. 「Kindle撮影PDF」（ホームの Applications フォルダ）をダブルクリックします。
4. 本の名前、ページ数（多めで大丈夫。同じ画面が2回続くと最後とみなして止まります）、向き（横書き／縦書き＝右から左）を入力して「開始」を押します。
5. 5秒後に Terminal が開いて撮影が始まります。終わるまで、マウスもキーボードも触りません。
6. 終わると Finder が保存先を開きます。PDF は `~/Documents/KindleCapture/本の名前.pdf`、画像は同じフォルダの `本の名前/` に入ります。

## 使い方（Terminal 版）

`cd ~/offline-pdf/Kindle2PDF && python3 kindle2pdf.py --name 本の名前 --pages 30 --direction left`

縦書きは `--direction left`、横書きは付けません。終了後にフォルダを開きたくないときは `--no-open` を付けます。オプションの間には必ずスペースを入れます（`3--direction` のようにくっつけるとエラーになります）。

## 困ったとき

- **同じページが何枚も撮れる／Kindle Classic が勝手に起動する：** アプリ名で前面に出す方式だと、別アプリの Kindle Classic が起動してキーがそちらに送られます。現在のスクリプトは、動作中のプロセス（`Kindle`）を System Events で前面に出す方式に直してあります。プロセス名は `osascript -e 'tell application "System Events" to get name of every process whose name contains "Kindle"'` で確認できます。
- **「osascriptには補助アクセスは許可されません (-1719)」：** アプリ自身から撮影を動かすと、アクセシビリティの許可が届きません。アプリは入力画面だけを担当し、撮影は許可済みの Terminal に任せる作りにしてあります。
- **アクセシビリティにアプリを登録できない：** 上のとおり、アプリには登録しなくて大丈夫です。Terminal だけに許可します。
- **画像が真っ黒：** 画面収録の許可を確認します。本によっては、Kindle が撮影を黒く隠します（この場合は撮れません）。
- **背景が黒で白文字になる：** Kindle の「Aa」で白に変えます。
- **(eval):1: no such file or directory: $/opt/homebrew/bin/brew：** `~/.zprofile` の記述の誤りによる表示で、動作には影響しません。

## メモ

- 現在は画像だけの PDF です。文字を検索できる PDF にする（OCR）のは今後の課題です。
- 更新したら、`~/offline-pdf` で `git add`、`git commit`、`git push` をします。
