あなたはUX TIMES用語集の「金曜・生成リクエスト消化バッチ」を実行するエージェント。詳細手順は /Users/takahashi_yuya/workspace/article-creator/pipeline/batch-instructions.md に従う。作業ディレクトリは /Users/takahashi_yuya/workspace/article-creator。.env に GAS_WEBAPP_URL / GAS_TOKEN / SLACK_DIGEST_CHANNEL がある。

このバッチは **Slackの生成リクエスト（`@用語くん ◯◯ の下書き作って`）がある時だけ**走らせる金曜ジョブ。月曜バッチと違い、金曜は「今週たまったリクエストを消化して、その場でSlack告知する」ところまでやる。

## Step 1: リクエストを抽出する
`gws sheets +read --spreadsheet 1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY --range "'UX TIMES 用語DB'!A1:R80" --format json` で用語DBを読む。
ステータス(H列)=「提案中」**かつ** 生成する(G列)=TRUE（＝生成リクエスト）の行だけを対象にする。ID昇順で最大5件。
- **対象が0件なら、生成もSlack投稿も一切せず終了する**（金曜は無リクエスト時は沈黙）。

## Step 2: 各件を生成（article-creator 無人モード）
選んだ各用語について `article-creator` スキルを無人モードで実行しドラフト生成する（batch-instructions.md の Step 2 の差分に従う）:
- 対話質問（AskUserQuestion）は一切しない。topic=用語、context=補足文脈(D列)、difficulty/it=0.3
- ディープリサーチは使わず WebSearch でソース収集
- WP重複チェックで既存記事が見つかったら生成せず「見送り」とし、Step 4 の update_row で status=「見送り」＋備考に既存URLを書く
- article-critic / article-review を内蔵で通し reviewed_at を付与。escalate ならDoc化せず記録
- drafts/{用語}.md に保存（frontmatter・アイキャッチプロンプト含む）
- UX TIMESは外部公開の一般記事。特定企業名（OPENLOGI等）に寄せない中立な解説にする

## Step 3: Doc化（記事ドラフトフォルダ）
生成できた各ドラフトについて、frontmatterを除去し、冒頭に「# {タイトル}」と次のレビュー案内行（イタリック）を付ける:
`*（レビュー用ドラフト：本文を直接編集してください。英字¥カタカナ¥ は読みがな記法、-- wp分割ライン -- は投稿時の区切りマーカーなので、そのまま残してください）*`
これを Google Drive の create_file で `contentMimeType=text/markdown`・`parentId=1tQU3-ts3mU6YusLFjijNDNGzdcf-y-GS` に作成する（自動でGoogleドキュメントに変換される）。作成された Doc の URL を控える。

## Step 4: 書き戻し（update_row webhook）
各件について .env の GAS_WEBAPP_URL に curl で POST する:
```
{"token":"<GAS_TOKEN>","action":"update_row","id":"G-xxx","status":"レビュー待ち","doc_url":"<DocURL>","generated_at":"<今日YYYY-MM-DD>","slug":"<frontmatterのslug>","excerpt":"<frontmatterのexcerpt>","category_id":<frontmatterのcategory_id>,"eyecatch_prompt":"<frontmatterのeyecatch_prompt>","flag":false}
```
`flag":false` で生成リクエスト（G列）を消化する。`eyecatch_prompt` はR列に入る。レスポンスの ok:true を確認する。見送りの場合は status=「見送り」・note に既存URL・`flag":false`。

## Step 5: Slackで告知する（金曜はこのバッチが投稿する）
生成できた件が1件以上あれば、`@用語くん` 名義でチャンネル（.env の SLACK_DIGEST_CHANNEL）に notify webhook で投稿する。GAS_WEBAPP_URL に curl で POST:
```
{"token":"<GAS_TOKEN>","action":"notify","channel":"<SLACK_DIGEST_CHANNEL>","text":"<投稿文>"}
```
投稿文の例（生成できた用語ぶんだけ Docリンクを列挙する。文面は用語くんらしく明るく）:
`:memo: リクエストいただいた下書きができたよ！レビューよろしく ✨\n・*用語名*（G-xxx）→ <DocURL>\n（レビューOKなら用語DBのステータスを「公開OK」にしてね）`
見送りだけで生成0件だったときは、その旨を短く告知する。

## Step 6: ログ
処理した用語・ステータス・DocURL・見送り/escalate理由を標準出力に簡潔にまとめる。criticスコア等の内部数値は出さない。
