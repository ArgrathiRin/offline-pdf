# Mac M1 (16GB) で PDF書籍を完全オフライン分析するマニュアル

構成: **Ollama(モデル実行)+ AnythingLLM Desktop(PDF取り込み・検索・チャット)**

- 対象環境: Apple Silicon Mac (M1) / メモリ16GB
- 目的: PDF書籍をローカルだけで分析する(RAG方式)
- 作成日: 2026-10-16

## 進捗

- [x] Ollama のインストール
- [x] モデルのダウンロード
- [x] 動作確認(日本語で自己紹介)
- [ ] AnythingLLM Desktop の導入
- [ ] PDFの取り込み
- [ ] オフライン動作の最終確認

## 1. モデルの選び方(16GBの目安)

macOSが使う分を除くと、モデルに回せるのは約10〜11GBです。

| 用途 | モデル | サイズ目安 | 備考 |
|---|---|---|---|
| 本命(日本語・精度のバランス) | `qwen3:14b`(Q4) | 約9GB | 日本語が強い。長いコンテキストでメモリ逼迫 |
| 軽快・安定重視 | `qwen3:8b` / `gemma3:12b` | 5〜8GB | 余裕があり、コンテキストを長く取れる |
| 埋め込み(検索用・必須) | `bge-m3` | 約1.2GB | 日本語を含む多言語に強い |

- 最初は8B〜12Bから始め、物足りなければ14Bを試す。
- 14Bはコンテキストを8,000〜16,000トークン程度に抑える(超えるとスワップして極端に遅くなる)。
- 32B以上は16GBでは実用にならない。
- モデル名は更新が速いので、最新は Ollama のライブラリで確認する。

## 2. Ollama の導入(ネット接続あり)

```bash
brew install ollama
brew services start ollama
```

## 3. モデルのダウンロード

```bash
ollama pull qwen3:8b
ollama pull qwen3:14b
ollama pull bge-m3
ollama list   # 入っているか確認
```

動作確認(ここまで完了済み):

```bash
ollama run qwen3:8b "日本語で自己紹介して"
```

## 4. AnythingLLM Desktop の導入

1. 公式サイト(anythingllm.com)から Mac(Apple Silicon)版をダウンロードしてインストール。
2. 初回設定:
   - LLM Provider: Ollama(URL: `http://127.0.0.1:11434`)、モデルは `qwen3:8b` など
   - Embedder: Ollama、モデルは `bge-m3`
   - Vector DB: LanceDB(デフォルト。ローカル保存)
3. Privacy / Telemetry 項目でテレメトリを無効化する。

## 5. PDFの取り込み

1. ワークスペースを作成(本1冊につき1ワークスペースが目安)。
2. アップロード画面でPDFを追加 →「Move to Workspace」→「Save and Embed」。
3. 質問すると、該当箇所を引用しながら回答する。

### スキャンPDF(画像PDF)の場合

文字が選択できないPDFは、先にOCRを行う。

```bash
brew install ocrmypdf tesseract tesseract-lang
ocrmypdf -l jpn+eng --skip-text input.pdf output.pdf
```

## 6. 完全オフラインにするための確認

1. 導入とモデルのダウンロードを、すべてネット接続ありで先に済ませる。
2. 一度オンラインで動作確認する。
3. Wi-Fiを切って、同じ操作ができるか確認する。
4. 必要に応じて、macOSのファイアウォールやLittle Snitchで、AnythingLLMとOllamaの外部通信をブロックする。

## 7. 分析のコツ

- 特定箇所への質問(「第3章の主張は?」)はRAGでうまく動く。
- 全体要約はRAGだと取りこぼしやすい。章ごとに要約させ、最後に章要約をまとめさせる。
- 根拠確認は「該当ページ・箇所を示して」と指示するか、AnythingLLMの引用表示で原文を確認する。
- 日本語書籍はチャンクサイズを大きめ(1,000〜1,500文字程度)にすると文脈が保たれる。

## 8. トラブル時の目安

- 動作が極端に遅い → コンテキストを短くする、または8Bモデルに切り替える。
- Ollamaに接続できない → `brew services list` で起動を確認、`brew services restart ollama`。
- 検索精度が低い → チャンクサイズ調整、PDFがOCR済みか確認。
