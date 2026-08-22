指定された1つの用語について記事ドラフトを作る。**対象用語は末尾の「対象用語:」で渡される**。作業ディレクトリは /Users/takahashi_yuya/workspace/article-creator。.env に GAS_WEBAPP_URL / GAS_TOKEN がある。

## Step 1: 用語DBの行を特定 / 用意
`gws sheets +read --spreadsheet 1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY --range "'UX TIMES 用語DB'!A1:L80" --format json` で用語DBを読み、対象用語が B列（用語）にあるか探す。
- あれば、その `ID`（G-xxx）と `補足・文脈`（D列）を使う。
- なければ、webhook で追加してIDを得る（.env の GAS_WEBAPP_URL に POST）：
  `{"token":"<GAS_TOKEN>","action":"add_term","silent":true,"term":"<対象用語>","proposer":"手動指定"}` → 返り値の id を使う。

## Step 2: 生成（article-creator 無人モード）
`article-creator` スキルを無人モードで実行する（`pipeline/batch-instructions.md` の Step 2 に従う）：
- 対話質問（AskUserQuestion）は一切しない。topic=対象用語、context=補足・文脈、difficulty/it=0.3
- ディープリサーチは使わず WebSearch でソース収集
- WP重複チェックで既存記事が見つかったら生成せず「見送り」（Step 4 で status=見送り＋備考に既存URL）
- critic / review を内蔵で通し reviewed_at を付与。escalate ならDoc化せず記録
- drafts/{対象用語}.md に保存。UX TIMESは外部公開の一般記事。特定企業名に寄せない中立な解説にする
- 保存したら `python3 scripts/stamp_version.py "drafts/{対象用語}.md"` を実行し、レシピ版をフロントマターに刻む

## Step 3: Doc化
frontmatterを除去し、冒頭に「# {タイトル}」と次のレビュー案内行（イタリック）を付ける：
`*（レビュー用ドラフト：本文を直接編集してください。英字¥カタカナ¥ は読みがな記法、-- wp分割ライン -- は投稿時の区切りマーカーなので、そのまま残してください）*`
Google Drive の create_file で `contentMimeType=text/markdown`・`parentId=1tQU3-ts3mU6YusLFjijNDNGzdcf-y-GS` に作成する。

## Step 4: 書き戻し（update_row webhook）
.env の GAS_WEBAPP_URL に POST：
`{"token":"<GAS_TOKEN>","action":"update_row","id":"G-xxx","status":"レビュー待ち","doc_url":"<DocURL>","generated_at":"<今日>","slug":"<frontmatterのslug>","excerpt":"<frontmatterのexcerpt>","category_id":<frontmatterのcategory_id>,"eyecatch_prompt":"<frontmatterのeyecatch_prompt>","creator_version":"<frontmatterのcreator_version>","recipe_hash":"<frontmatterのrecipe_hash>","flag":false}`

## Step 5: 報告
対象用語・ステータス・DocのURLを標準出力に出す。**Slackには投稿しない**（告知は月曜レポートがまとめて出す）。
