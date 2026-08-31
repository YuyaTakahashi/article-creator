指定された1つの用語について記事ドラフトを作る。**対象用語は末尾の「対象用語:」で渡される**。作業ディレクトリは /Users/takahashi_yuya/workspace/article-creator。.env に GAS_WEBAPP_URL / GAS_TOKEN がある。

## Step 1: 用語DBの行を特定 / 用意
`gws sheets +read --spreadsheet 1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY --range "'UX TIMES 用語DB'!A1:V1000" --format json` で用語DBを読み、対象用語が B列（用語）にあるか探す。
- あれば、その `補足・文脈`（D列）を Step 2 の context に使う。
- 無くてもここでは追加しない。Step 4 の `register_draft.py` が行の特定と新規追加を引き受ける。

## Step 2: 生成（article-creator 無人モード）
`article-creator` スキルを無人モードで実行する（`pipeline/batch-instructions.md` の Step 2 に従う）：
- 対話質問（AskUserQuestion）は一切しない。topic=対象用語、context=補足・文脈、difficulty/it=0.3
- ディープリサーチは使わず WebSearch でソース収集
- WP重複チェックで既存記事が見つかったら生成せず「見送り」（Step 4 で status=見送り＋備考に既存URL）
- article-critic を Step 5.5（リライト直後）と Step 8.5（保存直前）の2回とも必ず通す。escalate ならDoc化せず記録する。**`reviewed_at` は書かない**（article-review を実際に通したときだけ `scripts/mark_reviewed.py` が刻む印なので、生成段では付けない）
- drafts/{対象用語}.md に保存。UX TIMESは外部公開の一般記事。特定企業名に寄せない中立な解説にする
- 保存したら `python3 scripts/stamp_version.py "drafts/{対象用語}.md"` を実行し、レシピ版をフロントマターに刻む

## Step 3: Doc化
frontmatterを除去し、冒頭に「# {タイトル}」と次のレビュー案内行（イタリック）を付ける：
`*（レビュー用ドラフト：本文を直接編集してください。英字¥カタカナ¥ は読みがな記法、-- wp分割ライン -- は投稿時の区切りマーカーなので、そのまま残してください）*`
Google Drive の create_file で `contentMimeType=text/markdown`・`parentId=1tQU3-ts3mU6YusLFjijNDNGzdcf-y-GS` に作成する。

## Step 4: 書き戻し
次を実行する。フロントマターの読み取り・行の特定（無ければ新規追加）・全項目の書き戻しをスクリプトがまとめて行う。

```bash
python3 scripts/register_draft.py "drafts/{対象用語}.md" --doc-url "<Step 3のDocURL>"
```

出力の `完了: G-xxx / status=レビュー待ち / <DocURL>` を確認する。失敗したらそのまま報告する。

## Step 5: 報告
対象用語・ステータス・DocのURLを標準出力に出す。**Slackには投稿しない**（告知は月曜レポートがまとめて出す）。
