毎月「第1金曜日」に実行する、UX用語トレンド探索ジョブ。作業ディレクトリは /Users/takahashi_yuya/workspace/article-creator。.env に GAS_WEBAPP_URL / GAS_TOKEN / SLACK_DIGEST_CHANNEL がある。用語DBシート `1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY`（タブ「UX TIMES 用語DB」）。

## Step 1: トレンド探索（WebSearch）
WebSearch で、最近（直近〜数ヶ月）の UX/UI/AI/デザイン/プロダクトの**新しい用語・トレンド概念**を探す。UX TIMES用語集（一般公開の解説記事）に載せる価値がある、解説として成立する一般用語を候補にする（一過性のバズワードや商品名は避ける）。候補を8〜12件ほど広めに集める。

## Step 2: 既存と重複を除外
候補から、既に用語DBにあるものを除く。
`gws sheets +read --spreadsheet 1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY --range "'UX TIMES 用語DB'!B2:B120" --format json` でB列（用語）を読み、表記揺れ・日英・略称も考慮して被る候補を落とす。
（WP公開済みとの重複は、後段の記事生成時にWP重複チェックで「見送り」になるため、ここでは用語DBとの重複だけ厳密に見ればよい）

## Step 3: 用語DBに追加（3〜5件）
残った新規の候補から良いものを 3〜5件選び、.env の GAS_WEBAPP_URL に add_term でPOSTして追加する（提案中で入る）:
```
{"token":"<GAS_TOKEN>","action":"add_term","silent":true,"term":"<用語>","term_en":"<英語名 or 空>","context":"月次トレンド探索","proposer":"トレンド探索","note":"<なぜ今トレンドか一言>"}
```
返り値の id（G-xxx）を控える。

## Step 4: チャンネルに投稿（notify）
追加が済んだら .env の GAS_WEBAPP_URL に notify でPOSTし、SLACK_DIGEST_CHANNEL に用語くん名義で投稿する:
```
{"token":"<GAS_TOKEN>","action":"notify","channel":"<SLACK_DIGEST_CHANNEL>","text":":mag: 今月のトレンド用語を用語DBに追加したよ ✨\n• *用語A*（English）— 一言\n• *用語B* …\n気になるのがあったら書いてみてね 🌟"}"
```
レスポンスの ok:true を確認する。

## Step 5: ログ
追加した用語・除外した理由を標準出力に簡潔に出す。

補足: この日（第1金曜）はGAS側の通常の金曜DM（DB提案中からのサジェスト）はスキップされる。トレンド追加ぶんは、翌週以降の金曜DM・月曜レポートに自然に載る。
