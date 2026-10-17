-- Kindle 撮影 PDF（かんたんアプリ版）
-- kindle2pdf.py を、ダイアログで入力して実行するだけのアプリです。

set scriptDir to (POSIX path of (path to home folder)) & "offline-pdf/Kindle2PDF"

-- 1. 本の名前
set r1 to display dialog "本の名前を入力してください。（フォルダ名と PDF 名になります）" default answer "" with title "Kindle 撮影 PDF" buttons {"キャンセル", "次へ"} default button "次へ" cancel button "キャンセル"
set bookName to text returned of r1
if bookName is "" then
	display alert "本の名前が空です。" message "もう一度、アプリを開いてください。"
	return
end if

-- 2. ページ数
set r2 to display dialog "撮影するページ数を入力してください。（多めでも大丈夫です。最後のページで自動的に止まります）" default answer "30" with title "Kindle 撮影 PDF" buttons {"キャンセル", "次へ"} default button "次へ" cancel button "キャンセル"
try
	set pageCount to (text returned of r2) as integer
on error
	display alert "ページ数は数字で入力してください。"
	return
end try
if pageCount < 1 then
	display alert "ページ数は 1 以上にしてください。"
	return
end if

-- 3. 向き
set r3 to display dialog "本の向きを選んでください。" with title "Kindle 撮影 PDF" buttons {"キャンセル", "横書き", "縦書き（右から左）"} default button "縦書き（右から左）" cancel button "キャンセル"
if button returned of r3 is "横書き" then
	set dirOpt to "right"
else
	set dirOpt to "left"
end if

-- 4. 開始の確認
display dialog "Kindle を開き、撮り始めたいページを表示してください。" & return & return & "「開始」を押すと 5 秒後に撮影が始まります。撮影中は、マウスもキーボードも触らないでください。" with title "Kindle 撮影 PDF" buttons {"キャンセル", "開始"} default button "開始" cancel button "キャンセル"

set cmd to "cd " & quoted form of scriptDir & " && python3 kindle2pdf.py --name " & quoted form of bookName & " --pages " & pageCount & " --direction " & dirOpt

-- 画面収録とアクセシビリティの許可は、すでに設定済みの Terminal に任せます。
-- （アプリ自身に許可を付けなくても動くようにするためです）
tell application "Terminal"
	activate
	do script cmd
end tell
