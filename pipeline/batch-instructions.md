# UX用語バッチ生成パイプライン（用語DB → 記事生成 → Googleドキュメント）

2026-07-17 設計。7/13 AIエージェント会議（大本あかねさん×yuya）で合意した分業体制を実装する。
「AIが記事を量産し、人間はスプレッドシートとGoogleドキュメントだけで選別・レビューする」ことをゴールとする。
レビュアー（あかねさん・鹿児島さん）はClaude環境を必要としない。

## 全体アーキテクチャ

```
[提案]   用語くん（Slack app + GAS）／人間のシート直記入
            │ 用語を追記
            ▼
[DB]     スプレッドシート「UX TIMES 用語DB」（提案中＝これから書く用語の待ち行列）
            │ 提案中の行を処理順に取得（承認チェックは廃止）
            ▼
[生成]   Coworkバッチ（yuyaのMac・スケジュールタスク）
         article-creator無人モード → critic → article-review自動推敲
            │ drafts/{topic}.md 保存（アーカイブ兼WP投稿素材）
            ▼
[レビュー] Googleドキュメント（フォルダ「記事ドラフト」）
         あかねさんが編集 → シートのステータスを「公開OK」へ
            │
            ▼
[公開]   DocをMDに再取込 → post_to_wp.py（ローカル実行）→ WP下書き → WP上で公開
```

## 固定ID

| リソース | ID / URL |
|---|---|
| 用語DBシート | `1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY` |
| 記事ドラフトフォルダ | `1tQU3-ts3mU6YusLFjijNDNGzdcf-y-GS` |
| 親フォルダ | `1ZJM_GhPN2ku7NESBsDq8l7QgtuGCIM51` |

## シートの列とステータス

列（A–L）: `ID / 用語 / 英語名 / 補足・文脈 / 提案元 / 提案日 / 生成する / ステータス / 記事Doc / WP URL / 生成日 / 備考`
列（M–R, 公開OK→WP下書き作成・画像入れに使用）: `slug / excerpt / category_id / featured_media / wp_post_id / eyecatch_prompt`（生成時に update_row でフロントマターから埋める。R「eyecatch_prompt」はClaude無しで画像を自作する人向けの元プロンプト）
列（S–V, レシピ版管理）: `生成バージョン / レシピhash / 作り直し / 作り直しメモ`
G「生成する」列は、Slackの生成リクエスト（`@用語くん ◯◯ の下書き作って`）で TRUE が立つフラグ。月曜バッチが最優先で拾い（金曜バッチはこれがある時だけ走る）、生成後に update_row の `flag:false` で消化する。
U「作り直し」列は、Slackの作り直しリクエスト（`@用語くん ◯◯ を最新版で作り直して`）で TRUE が立つフラグ。**すでに下書きがある用語を、最新レシピで書き直す**ためのもので、G列（下書きがまだ無い用語の新規生成）とは別物。生成後に update_row の `regen:false` で消化する。
S「生成バージョン」列には、その記事を作ったときのレシピ版（`v3` など）が入る。空欄はバージョン管理を始める前に作った記事を指す。

| ステータス | 意味 | 遷移させる主体 |
|---|---|---|
| 提案中 | 用語くん・人間が提案した直後 | 用語くん／人間 |
| レビュー待ち | 記事を生成しDoc化済み | パイプライン |
| 公開OK | 人間がDocレビューを終えた | 人間 |
| 下書き作成済み | スプシメニューでGASがWP下書きを作成した | メニュー(GAS) |
| 公開済み | WPで公開した | パイプライン／人間 |
| 作り直し済み | 公開中の記事を最新レシピで書き直し、新しいDocがレビュー待ち | パイプライン |
| 見送り | 重複・不適合などで生成しない | パイプライン／人間 |

## バッチ実行手順（Cowork側）

### Step 1: シート読取

`read_file_content`（Drive連携）でシートを読み、**ステータス=提案中** の行を抽出する（承認チェック「生成する」は廃止。G列は使わない）。
処理順は **⓪ 作り直しリクエスト（U列=TRUE）を最優先 → ① Slackで用語くんに追加された用語（提案元に「Slack」を含む）を優先 → ② 残りは登場回数（備考に記録した本数）が多い順、同数ならID昇順**。
作り直しは1回の実行で**最大2件**までにする（レビューする人の負担が新規生成より重いため）。**新規と合わせて1回3件が上限**で、作り直しが入った週は新規の本数を減らす。あふれた分はフラグが立ったまま残り、次の実行で拾われる。
**1回の実行で最大3本**を処理する（**毎週月曜10:00に自動実行**。増やすときはMTG合意後に変更する）。

### Step 2: 記事生成（article-creator 無人モード）

article-creator の Step 1〜6 を以下の差分つきで実行する：

- 対話質問（AskUserQuestion）は一切行わない。topic=シートの用語、context=補足・文脈、difficulty/it=0.3
- Step 0-b のディープリサーチ（NotebookLM/Chrome）は無人実行では壊れやすいため、**WebSearchによるソース収集で代替**する。重要用語は後から手動でディープリサーチつき再生成できる
- WP重複チェックで既存記事が見つかったら、生成せず**ステータス=見送り**＋備考に既存記事URLを書いて次へ進む
- article-critic の往復・article-review の自動推敲まで内部で完結させ、`reviewed_at` を付与する（人間レビュー前のAI品質ゲート）
- critic が escalate になった記事は**Doc化せず**、yuyaへの報告にのみ出す

`drafts/{topic}.md` への保存は従来どおり行う（フロントマター・アイキャッチプロンプトはWP投稿時に使うため、MDが正式なアーカイブとなる）。

**保存したら必ずレシピ版を刻む**（どの版で書いたかを記事側に残さないと、あとで作り直す判断ができない）：

```bash
python3 scripts/stamp_version.py "drafts/{topic}.md"
```

これで `creator_version` / `recipe_hash` / `generated_at` がフロントマターに入る。刻印した `creator_version` は Step 4 の書き戻しでそのまま送る。

#### 作り直し（U列=TRUE）のときの差分

1. 上書きされる前に、いまの `drafts/{topic}.md` を `drafts/_archive/{topic}_{旧版}_{YYYY-MM-DD}.md` へ退避する（旧版が消えると前後比較ができなくなる）
2. 生成は新規と同じ手順で行う。前の本文は参照せず、最新レシピでゼロから書く
3. 刻印は作り直し元の版を添えて行う：`python3 scripts/stamp_version.py "drafts/{topic}.md" --regenerated-from {旧版}`

### Step 3: Googleドキュメント化

1. フロントマターを取り除く
2. 冒頭に `# {タイトル}` と、レビュー案内の1行（イタリック）を付ける：
   `*（レビュー用ドラフト：本文を直接編集してください。英字¥カタカナ¥ は読みがな記法、-- wp分割ライン-- は投稿時の区切りマーカーなので、そのまま残してください）*`
3. `create_file`（Drive連携）で `contentMimeType: text/markdown`・`parentId: 記事ドラフトフォルダ` を指定して作成する（自動でGoogleドキュメントに変換される）

作り直し（U列=TRUE）のときは、**旧Docを消さず新しいDocを作る**。人が旧Docに入れた編集を消さないためで、レビュー案内の1行の後ろに次を足して、どちらが新しいか分かるようにする：

`*（{新版} で作り直した版です。前の版はこちら: {旧DocのURL}）*`

用語DBのI列（記事Doc）は新Docに差し替え、旧DocのURLは備考(L列)に `旧版{旧版}: {旧DocURL}` の形で残す。

### Step 4: シート書き戻し

GAS Webhook（`pipeline/gas-webhook.gs` をシートにデプロイしたもの）を **Desktop Commander経由のローカルcurl** で叩く：

```bash
curl -s -X POST "{GAS_WEBAPP_URL}" -H "Content-Type: application/json" -d '{
  "token": "{SECRET_TOKEN}",
  "action": "update_row",
  "id": "G-XXX",
  "status": "レビュー待ち",
  "doc_url": "{DocのURL}",
  "generated_at": "YYYY-MM-DD",
  "slug": "{フロントマターのslug}",
  "excerpt": "{フロントマターのexcerpt=最小限の説明}",
  "category_id": {フロントマターのcategory_id},
  "featured_media": {フロントマターのfeatured_media},
  "wp_post_id": {あれば},
  "eyecatch_prompt": "{フロントマターのeyecatch_prompt}",
  "creator_version": "{フロントマターのcreator_version}",
  "recipe_hash": "{フロントマターのrecipe_hash}",
  "flag": false
}'
```

作り直し（U列=TRUE）のときは、これに加えて次を送る：

- `"regen": false` … 作り直しリクエスト（U列）の消化
- `"status"` … 元が **公開済み** だった場合は `"作り直し済み"`（WPで公開中の本文は旧版のままなので「レビュー待ち」にはしない）。それ以外は `"レビュー待ち"`
- `"note"` … `旧版{旧版}: {旧DocURL}` を残す
- `"regen_note"` … `{YYYY-MM-DD} {旧版} → {新版} で作り直し`

`slug / excerpt / category_id / featured_media / wp_post_id / eyecatch_prompt` は、後段の「公開OK→WP下書き作成」（Phase 3）や画像入れでGAS・人が使う。
生成時にフロントマターから必ず一緒に送り、シートのM〜R列を埋めておく（Docにはフロントマターが残らないため、シートが唯一の取得元になる）。`eyecatch_prompt`（R列）は、Claude Codeが無い人がChatGPT/Geminiで自分で画像を作るときの元プロンプトになる。`flag:false` は生成リクエスト（G列）の消化。

GAS未デプロイの間は、書き戻し内容をチャットで報告してyuyaに手動更新を依頼する（ブロッカーにしない）。
Coworkサンドボックスから外部HTTPSは403になるため、**curlは必ずローカル（Desktop Commander）で実行する**。

### Step 5: 週次ダイジェストをSlackに投稿（用語くん名義）

3本ぶんの生成・Doc化・`update_row`書き戻しが終わったら、**用語くん名義でSlackにまとめて投稿**する。
bot token は用語くん(GAS 1q0O)側にあるので、ローカルからは用語くんの `notify` アクションに投稿を委譲する：

```bash
curl -s -X POST "{GAS_WEBAPP_URL}" -H "Content-Type: application/json" -d '{
  "token": "{GAS_TOKEN}", "action": "notify",
  "channel": "{Slack投稿先チャンネルID}",
  "text": ":sparkles: 今週のドラフト、3本できたよ！レビューして「公開OK」にしてね\n• {用語A} → {DocURL}\n• {用語B} → {DocURL}\n• {用語C} → {DocURL}"
}'
```

既存重複で見送った用語があれば、本文末尾に「（今週は {用語} を既存重複で見送り）」と一言添える。

### Step 6: 完了報告

処理した用語・ステータス・DocURL・見送り/保留の理由を簡潔に報告する。criticスコア等の内部情報は出さない（escalate時を除く）。

## 公開フロー（Phase 3・スプシメニューでGASがWP下書きを作成）

レビュアーがDoc編集を終えたら、シートで対象行を1つ選び **メニュー「用語くん」→「▶ 選択行をWP下書きに送る」** を押す。GAS（`publishRowToWpDraft_`）が次を行う：

1. M〜Q列（slug/excerpt/category_id/featured_media/wp_post_id）とI列のDoc URLを読む
2. DocをMarkdownとしてエクスポート（Drive export `text/markdown`）し、冒頭のレビュー案内行を除去
3. 本文をHTML化（ルビ `英字¥カナ¥`→`<ruby>`、`wp分割ライン`→`<!--nextpage-->`、見出しはh2起点）
4. `POST {WP_SITE_URL}/wp-json/wp/v2/{WP_POST_TYPE}` に `status:draft` で送る（`wp_post_id` があれば更新し、WP側の公開状態は保持）
5. 返ってきた WP URL と `wp_post_id` をシート（J列・Q列）に書き戻し、ステータスを「下書き作成済み」に更新
6. 最終公開はWP管理画面で人間が行う

WP認証はGASのスクリプトプロパティに置く: `WP_SITE_URL / WP_USER / WP_APP_PASS / WP_POST_TYPE(=glossary) / WP_CATEGORY_FIELD(=glossary-category)`。
初回メニュー実行時に Drive読取スコープの認可ダイアログが出る（一度きり）。

補足:
- **Docへ移した後の本文はDoc側が正**。`wp_post_id` 付きの再生成・上書きはAI側から原則行わない（人間の編集を消す事故防止）。
- GASのmd→HTMLは `post_to_wp.py` ほど枯れていないので、**最初の1本は生成物をWPプレビューで確認**してから運用に乗せる。品質が要る用語は従来どおりローカル `post_to_wp.py` 経路も併用できる。
- `## 関連用語` の `>`（引用符）復元はGAS側で未対応。必要ならDoc側で残す運用にするか、後で対応を追加する。

## 用語くん（Phase 2・GAS + Slack app）

- 実装場所: UX DAYS TOKYO側Slackワークスペース（Cowork連携外のため独立実装）
- GAS雛形: `pipeline/gas-webhook.gs`（受付・書き戻し・Slack通知・週次ダイジェストまで実装済み。Slackメンション受付はTODOコメント参照）
- AI提案の頭脳はCowork側が担う: 週次ジョブが既存記事の「関連用語の未作成リンク」等から候補を抽出し、GAS `add_term` でシートに積む → 用語くんがSlackに提案を投稿する

## 残作業チェックリスト

- [ ] yuya: シート・フォルダをあかねさんに共有する（OPENLOGIアカウントの外部共有制限に注意。不可ならUX DAYS TOKYO側アカウントで作り直し、IDをこのファイルで差し替える）
- [x] yuya: シートにApps Scriptをclaspでデプロイ、URLとトークンを `.env` に追記済み（`GAS_WEBAPP_URL` / `GAS_TOKEN`）。デプロイ実体は `pipeline/gas/`（gitignore）
- [ ] yuya: WP下書き用にGASのスクリプトプロパティを設定（`WP_SITE_URL` / `WP_USER` / `WP_APP_PASS` / `WP_POST_TYPE=glossary` / `WP_CATEGORY_FIELD=glossary-category`）→ メニュー「▶ 選択行をWP下書きに送る」で初回認可を通し、1本テスト
- [ ] MTG合意後: スケジュールタスク登録（平日朝1本を推奨）
- [ ] Phase 2: Slack appを作成し用語くんを常駐させる（用語くん経由で「公開OK」を伝える経路もここで開通）
