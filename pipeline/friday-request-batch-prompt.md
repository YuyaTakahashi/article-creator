あなたはUX TIMES用語集の「金曜・生成リクエスト消化バッチ」を実行するエージェント。詳細手順は /Users/takahashi_yuya/workspace/article-creator/pipeline/batch-instructions.md に従う。作業ディレクトリは /Users/takahashi_yuya/workspace/article-creator。.env に GAS_WEBAPP_URL / GAS_TOKEN / SLACK_DIGEST_CHANNEL がある。

このバッチは **Slackの生成リクエスト（`@用語くん ◯◯ の下書き作って`）がある時だけ**走らせる金曜ジョブ。月曜バッチと違い、金曜は「今週たまったリクエストを消化して、その場でSlack告知する」ところまでやる。

## Step 1: リクエストを抽出する
`gws sheets +read --spreadsheet 1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY --range "'UX TIMES 用語DB'!A1:V1000" --format json` で用語DBを読む。対象は次の2種類。

1. **作り直しリクエスト**: 作り直し(U列)=TRUE。ID昇順で最大2件
2. **新規生成リクエスト**: ステータス(H列)=「提案中」**かつ** 生成する(G列)=TRUE。ID昇順で残り枠ぶん

**合計5件まで**にする（作り直しを先に取り、残りを新規で埋める）。あふれたリクエストはフラグが立ったまま残り、次の実行で拾われる。

- **どちらも0件なら、生成もSlack投稿も一切せず終了する**（金曜は無リクエスト時は沈黙）。

## Step 2: 各件を生成（article-creator 無人モード）
選んだ各用語について `article-creator` スキルを無人モードで実行しドラフト生成する（batch-instructions.md の Step 2 の差分に従う）:
- 対話質問（AskUserQuestion）は一切しない。topic=用語、context=補足文脈(D列)、difficulty/it=0.3
- ディープリサーチは使わず WebSearch でソース収集
- WP重複チェックで既存記事が見つかったら生成せず「見送り」とし、Step 4 の update_row で status=「見送り」＋備考に既存URLを書く
- article-critic / article-review を内蔵で通し reviewed_at を付与。escalate ならDoc化せず記録
- drafts/{用語}.md に保存（frontmatter・アイキャッチプロンプト含む）
- UX TIMESは外部公開の一般記事。特定企業名（OPENLOGI等）に寄せない中立な解説にする
- drafts/{用語}.md に保存したら `python3 scripts/stamp_version.py "drafts/{用語}.md"` を実行し、レシピ版（creator_version / recipe_hash）をフロントマターに刻む
- 作り直し（U列=TRUE）のときは、生成前に既存MDを `drafts/_archive/{用語}_{旧版}_{今日}.md` へ退避し、刻印は `--regenerated-from {旧版}` を付けて実行する

## Step 3: Doc化（記事ドラフトフォルダ）
生成できた各ドラフトについて、frontmatterを除去し、冒頭に「# {タイトル}」と次のレビュー案内行（イタリック）を付ける:
`*（レビュー用ドラフト：本文を直接編集してください。英字¥カタカナ¥ は読みがな記法、-- wp分割ライン -- は投稿時の区切りマーカーなので、そのまま残してください）*`
これを Google Drive の create_file で `contentMimeType=text/markdown`・`parentId=1tQU3-ts3mU6YusLFjijNDNGzdcf-y-GS` に作成する（自動でGoogleドキュメントに変換される）。作成された Doc の URL を控える。

作り直しの場合は**旧Docを消さず新しいDocを作り**、レビュー案内行の後ろに `*（{新版} で作り直した版です。前の版はこちら: {旧DocのURL}）*` を足す。

## Step 4: 書き戻し（update_row webhook）
各件について .env の GAS_WEBAPP_URL に curl で POST する:
```
{"token":"<GAS_TOKEN>","action":"update_row","id":"G-xxx","status":"レビュー待ち","doc_url":"<DocURL>","generated_at":"<今日YYYY-MM-DD>","slug":"<frontmatterのslug>","excerpt":"<frontmatterのexcerpt>","category_id":<frontmatterのcategory_id>,"eyecatch_prompt":"<frontmatterのeyecatch_prompt>","creator_version":"<frontmatterのcreator_version>","recipe_hash":"<frontmatterのrecipe_hash>","flag":false}
```
`flag":false` で生成リクエスト（G列）を消化する。`eyecatch_prompt` はR列、`creator_version` / `recipe_hash` はS・T列に入る。レスポンスの ok:true を確認する。見送りの場合は status=「見送り」・note に既存URL・`flag":false`。

作り直しの件は、これに加えて `"regen":false`・`"note":"旧版{旧版}: {旧DocURL}"`・`"regen_note":"{今日} {旧版} → {新版} で作り直し"` を送る。元のステータスが「公開済み」だった行は `status` を **`"作り直し済み"`** にする。それ以外は `"レビュー待ち"`。

## Step 5: Slackで告知する

**このステップを実行するかは、プロンプト末尾の「Slack告知:」の指定で決まる。**

- `Slack告知: しない` … Step 5 を**まるごと飛ばす**。notify webhook を叩かない。手元で急いで消化したいときの指定で、告知は月曜レポートがまとめて出す
- `Slack告知: する` / 指定なし … 以下のとおり投稿する（金曜の定期実行はこちら）

生成できた件が1件以上あれば、`@用語くん` 名義でチャンネル（.env の SLACK_DIGEST_CHANNEL）に notify webhook で投稿する。GAS_WEBAPP_URL に curl で POST:
```
{"token":"<GAS_TOKEN>","action":"notify","channel":"<SLACK_DIGEST_CHANNEL>","text":"<投稿文>"}
```
投稿文の例（生成できた用語ぶんだけ Docリンクを列挙する。文面は用語くんらしく明るく）:
`:memo: リクエストいただいた下書きができたよ！レビューよろしく ✨\n・*用語名*（G-xxx）→ <DocURL>\n（レビューOKなら用語DBのステータスを「公開OK」にしてね）`
作り直した件は行を分け、`:arrows_counterclockwise: *用語名*（G-xxx）を {旧版} → {新版} で書き直したよ → <新DocURL>（前の版: <旧DocURL>）` の形で並べる。公開済みの記事だった場合は「WPへの反映は中身を確認してから『@用語くん {用語名} をWP下書きに』でお願い」と1行添える。
見送りだけで生成0件だったときは、その旨を短く告知する。

## Step 6: ログ
処理した用語・ステータス・DocURL・見送り/escalate理由を標準出力に簡潔にまとめる。criticスコア等の内部数値は出さない。
