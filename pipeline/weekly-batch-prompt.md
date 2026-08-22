あなたはUX TIMES用語集の「週次ドラフト生成バッチ」を実行するエージェント。詳細手順は /Users/takahashi_yuya/workspace/article-creator/pipeline/batch-instructions.md に従う。作業ディレクトリは /Users/takahashi_yuya/workspace/article-creator。.env に GAS_WEBAPP_URL / GAS_TOKEN / SLACK_DIGEST_CHANNEL がある。以下を順に実行せよ。

## Step 1: 対象3件を選ぶ
`gws sheets +read --spreadsheet 1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY --range "'UX TIMES 用語DB'!A1:V80" --format json` で用語DBを読む。

**1回の実行で扱うのは合計3件まで**（レビューする人の負担を一定に保つため、作り直しが入った週は新規を減らす）。
まず **作り直しリクエスト（U列=TRUE）** をID昇順で最大2件取る。これは「すでに下書きがある記事を最新レシピで書き直す」依頼。
残った枠を ステータス(H列)=「提案中」の行で埋める。次の優先度で選ぶ。どちらも0件なら何もせず終了する。
- 優先① 生成する(G列)=TRUE（Slackの「下書き作って」生成リクエスト）を最優先
- 優先② 提案元(E列)に「Slack」を含む行
- 優先③ 残りは備考(L列)の「公開記事N本」のNが大きい順、同数はID昇順

※生成リクエスト（G列=TRUE）が4件以上あるときは、この月曜バッチでは上位3件まで。残りは金曜バッチ（リクエストがある時だけ走る）が拾う。作り直しリクエストのあふれも同様に次回へ回す。

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
`eyecatch_prompt` はフロントマターの値をそのまま送る（用語DBのR列に入り、Claudeが無い人が自分で画像を作るときに使う）。`creator_version` / `recipe_hash` は刻印した値をそのまま送る（S・T列に入る）。`flag:false` で生成リクエスト（G列）を消化する。レスポンスの ok:true を確認する。見送りの場合は status=「見送り」・note に既存URL。

作り直しの件は、これに加えて `"regen":false`・`"note":"旧版{旧版}: {旧DocURL}"`・`"regen_note":"{今日} {旧版} → {新版} で作り直し"` を送る。元のステータスが「公開済み」だった行は `status` を **`"作り直し済み"`** にする（WPで公開中の本文は旧版のままなので「レビュー待ち」にはしない）。それ以外は `"レビュー待ち"`。

## Step 5: Slack投稿はしない（月曜レポートに委譲）
このバッチは **Slackに投稿しない**。生成・Doc化・`update_row` の書き戻しまでで完了する。
今週できたドラフトの告知は、用語くん(GAS)の月曜レポート（毎週月曜11時 `sendMondayReport`）が用語DBを読んでまとめて投稿する（公開祝い・みんなの状況・未公開ドラフト数・今週できた3本Docリンクを1本に統合）。バッチは11時より前（10時開始）に書き戻しを終える。

## Step 6: ログ
処理した用語・ステータス・DocURL・見送り/escalate理由を標準出力に簡潔にまとめる。criticスコア等の内部数値は出さない。
