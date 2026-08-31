---
name: article-post
description: |
  drafts/ フォルダのMDファイルをWordPressに新規下書き投稿または既存投稿の更新として送るCoworkスキル。
  article-creator で生成したMDを人間が確認・編集したあとに呼び出す。

  以下のリクエストで必ず使用する：
  - 「article-post で○○.mdを投稿して」「このMDをWordPressに下書き投稿して」
  - 「drafts/○○.mdをWPに送って」「用語集にこのMDを反映して」
  - 「article-postしたい」「/article-post ○○.md」
  - article-creator の完了報告のあと「投稿まで進めて」と頼まれたとき
  フロントマターの wp_post_id の有無で新規作成 / 更新を自動切り替えする。
compatibility: "ユーザーの ~/workspace/article-creator フォルダがマウントされていること、または mcp__cowork__request_cowork_directory で要求可能であること"
---

# article-post スキル（Cowork版）

`drafts/` フォルダに保存されたMDファイルを読み込み、HTMLに変換してWordPressに投稿する。

- **新規作成モード**: フロントマターに `wp_post_id` が無い場合、新しい下書きをPOSTする
- **更新モード**: フロントマターに `wp_post_id` がある場合、その投稿を更新する

> ## ⚠️ 最重要・毎回必ず守る：WordPressへのPOSTはローカル実行のみ
>
> Coworkのサンドボックス（`mcp__workspace__bash`）は外部HTTPSに到達できない。WordPress（`uxdaystokyo.com`）へ`curl`/`urllib`で接続するとHTTP 000で失敗する。**サンドボックスから直接POSTしようとしないこと。**
>
> 最終的なWP投稿は、ユーザーが自分のMac上でローカルに次を実行して行う：
>
> ```
> cd ~/workspace/article-creator && python3 scripts/post_to_wp.py drafts/{filename}.md
> ```
>
> したがってCowork側の役割は「`drafts/{filename}.md` を投稿可能な状態まで完成させる」ところまで。具体的には、本文の確定・提唱者ポートレートや挿絵の埋め込み（`post_to_wp.py` の `md_to_html` を通る形式で）・フロントマターの整備までを行い、最後にローカル実行コマンドをユーザーに提示する。
>
> 以降のStep 5に「bashからPOSTする」手順があっても、それはローカル実行に読み替える。サンドボックスからのPOSTは毎回失敗するので試さない。

> ## 画像スタイル（必ず守る）
> - **アイキャッチ**：`style-guide-eyecatch.md` 上部のハウススタイル（クリーム背景・フラット線画）。`scripts/generate_eyecatch.py` で生成。
> - **記事本文の挿絵**：`style-guide-eyecatch.md` の「挿絵スタイル（NotebookLM風）」セクションに従う（白背景・幾何学フラット・こども向けキャッチー・日本語ラベルのみ・ロゴ/ウォーターマーク/「cite:x」禁止・1章1ファイル・連番なし）。`scripts/gen_image.py` で生成。
> - 画像生成は時間がかかるため、複数枚は**並列実行**する。
> - `scripts/post_to_wp.py` が次を自動処理する：Markdownの表→`<table>`変換／`<figure>`等の生HTML行の素通し／本文中のローカル画像（`src="drafts/..."`）のWPメディア自動アップロード＆URL置換／フロントマター `eyecatch_image`→アップロードして `featured_media` 設定。挿絵やアイキャッチは `drafts/...` のローカルパスで本文・フロントマターに置けばよい（POST時にURL化される）。

> ## ⚠️ WordPressを「正」とする（既存記事を更新するときの鉄則）
>
> `wp_post_id` がある記事の更新で `post_to_wp.py` の更新モードを使うと、title / content / excerpt / category をローカルMDで**丸ごと上書き**する。WP側で直した本文があれば消える。ローカルMDがWPより古い可能性があるときは、WP本文を上書きしない。
>
> - **アイキャッチだけ載せたい／WP本文を正のまま保ちたい**ときは、本文に触れない専用スクリプトを使う：
>
>   ```
>   cd ~/workspace/article-creator && python3 scripts/upload_eyecatch.py drafts/{filename}.md
>   ```
>
>   これは `featured_media`（アイキャッチ）だけを PATCH し、WPの本文・タイトル・抜粋・カテゴリには一切触れない。フロントマターに `wp_post_id` と `eyecatch_image` があれば動く。
> - 本文ごとローカルMDで上書きしてよいと**確信できるときだけ** `post_to_wp.py` の更新モードを使う。ローカルが最新だと言い切れないときは、先にWP側を確認するか、上の局所更新（アイキャッチのみ等）を選ぶ。

---

## Step 0: リポジトリのマウントと設定読み込み

### 0-1. 作業フォルダの確保

```bash
ls /sessions/*/mnt/article-creator/.env 2>/dev/null && echo "MOUNTED" || echo "NOT_MOUNTED"
```

`NOT_MOUNTED` の場合は `mcp__cowork__request_cowork_directory` を `path="~/workspace/article-creator"` で呼び出し、ユーザーに承認してもらう。

```bash
REPO_BASH=$(ls -d /sessions/*/mnt/article-creator 2>/dev/null | head -1)
if [ -z "$REPO_BASH" ]; then
  echo "ERROR: article-creator がマウントされていません" >&2
  exit 1
fi
```

Read/Write/Edit ツールは `/Users/takahashi_yuya/workspace/article-creator/` を使う。

### 0-2. .env の読み込み

```bash
if [ ! -f "$REPO_BASH/.env" ]; then
  echo "ERROR: $REPO_BASH/.env が存在しません" >&2
  exit 1
fi
set -a
source "$REPO_BASH/.env"
set +a
WP_PASS_CLEAN=$(echo "$WP_APP_PASS" | tr -d ' ')
```

---

## Step 1: 引数を対話で収集

スキル起動メッセージにファイル名が含まれていればそれを使う。含まれていなければ `AskUserQuestion` で聞く。

### 質問1: filename（必須）

```
投稿するMDファイル名を指定してください。
drafts/ フォルダ配下のファイル名のみで構いません（例: プロプライエタリ・テクノロジー.md）。
```

`drafts/` に該当ファイルが存在しない場合は、`ls /Users/takahashi_yuya/workspace/article-creator/drafts/` の結果を提示して再選択させる。

---

## Step 2: MDファイルの読み込みとパース

`/Users/takahashi_yuya/workspace/article-creator/drafts/{filename}` を Read ツールで読み込む。

YAMLフロントマターから以下を取得する：

| フィールド | 必須 | 用途 |
|---|---|---|
| `title` | ○ | WP投稿タイトル |
| `excerpt` | ○ | WP投稿抜粋 |
| `category_id` | ○ | カテゴリID |
| `category_field` | ○ | タクソノミーフィールド名（例: `glossary-category`） |
| `wp_post_id` | △ | 既存投稿のID。ある場合は更新モード、無い場合は新規作成モード |
| `eyecatch_prompt` | - | 完了報告に出力（WP投稿には使わない） |

フロントマター終端（`---` の2行目）以降の全テキストを記事本文として扱う。

### 投稿前ゲート: article-review を通したか確かめる

`scripts/post_to_wp.py` は投稿とメディアアップロードの前に `reviewed_at` と `logs/review/` の実施ログを照合し、そろっていなければ投稿を止める。次の2つのときに止まる。

- **`reviewed_at` が無い** → 推敲していない。`/article-review {ファイル名}.md` を先に実行する
- **`reviewed_at` はあるが実施ログが無い** → 生成側が自己申告で刻んだ印である。あらためて `/article-review {ファイル名}.md` を実行する

ゲートで止まったら、その場で `--skip-review-gate` を付けて押し通さない。**yuya に理由を伝えて、article-review を通すか、それでも投稿するかを決めてもらう。** WordPress への反映は巻き戻しづらいので、判断を代行しない。

---

## Step 3: HTML変換

以下の変換ルールを適用してMarkdownをHTMLに変換する：

| Markdown | HTML |
|---|---|
| `## 見出し` | `<h2>見出し</h2>` |
| `### 見出し` | `<h3>見出し</h3>` |
| `**太字**` | `<strong>太字</strong>` |
| `*斜体*` | `<em>斜体</em>` |
| `- リスト項目`（先頭スペースあり ` - ` も同様） | `<ul><li>リスト項目</li></ul>` |
| 段落（空行区切り） | `<p>...</p>` |
| `[A-Za-z0-9.\-]+¥カタカナ¥` | `<ruby>英字<rt>カタカナ</rt></ruby>` |

リスト行の判定は `line.strip().startswith('- ')` で行い、先頭スペースを無視する。
ruby タグの変換は `[A-Za-z0-9.\-]+` で英数字のみにマッチさせ、日本語文字を取り込まない。

変換は Bash 上の Python スクリプトで行う。生成したHTMLを一時ファイル（`/tmp/article_html.txt`）に書き出し、後続ステップで使う。

---

## Step 4: 提唱者の顔画像挿入

### 人物名の抽出

HTML変換後の `<h2>語源・提唱者</h2>` セクション内のテキストから、`<ruby>` タグ内の英語部分（人物名）を抽出する。抽出結果はJSON配列で管理する。

例: `["Louis Pouzin", "Glenda Schroeder", "Ken Thompson"]`

企業名・製品名（Apple, Microsoft, IBM など）は対象外とし、人物名のみを対象とする。

### 各人物のポートレート検索（優先順位順）

- `WebSearch` で `"{person_name}" site:en.wikipedia.org` を検索してWikipedia記事URLを特定する
- `WebFetch`（または `mcp__workspace__web_fetch`）でそのWikipedia記事を取得し、`upload.wikimedia.org` で始まるポートレート画像URLを抽出する
- Wikimedia で見つからない場合は `"{person_name}" portrait photo` で再検索する
- Wikimedia 等に自由利用できる肖像が無い場合は、本人の公式サイト等の写真を**出典を明記したうえでホットリンク**してよい（権利が不明な画像は避ける）。それも無ければ `None` としてスキップする

選定禁止: 図解・グラフ・ロゴ・風景。顔写真（ポートレート）のみ選ぶ。

### 画像HTMLの生成と挿入

**画像は小さめ（幅200px程度）**にし、**説明文と出典URLはキャプション（figcaption）**に入れる（画像のdescription/alt任せにしない）。

```html
<figure style="max-width:220px;"><img src="{image_url}" alt="{name_katakana}" width="200" style="max-width:200px;height:auto;"><figcaption>{ひとことの説明}（{name_katakana}）／出典: <a href="{source_page_url}" target="_blank" rel="noopener">{source_page_url}</a></figcaption></figure>
```

その人物名（英語）が `<ruby>` タグで最初に登場する `</p>` の直後に挿入する。
見つからない場合は `<h2>語源・提唱者</h2>` の直後に挿入する。

---

## Step 5: WP REST APIへのPOST

フロントマターの `wp_post_id` の有無で、エンドポイントとペイロードを切り替える。

```bash
export WP_TITLE="$title"
export WP_EXCERPT="$excerpt"
export WP_CATEGORY_ID="$category_id"
export WP_CATEGORY_FIELD="$category_field"
export WP_POST_ID="${wp_post_id:-}"
export WP_HTML_PATH=/tmp/article_html_with_portraits.txt
python3 - <<'PY'
import os, urllib.request, json, base64
WP_SITE_URL = os.environ["WP_SITE_URL"]
WP_USER = os.environ["WP_USER"]
WP_PASS_CLEAN = os.environ["WP_PASS_CLEAN"]
WP_POST_TYPE = os.environ.get("WP_POST_TYPE", "posts")
title = os.environ["WP_TITLE"]
excerpt = os.environ["WP_EXCERPT"]
category_id = int(os.environ["WP_CATEGORY_ID"])
category_field = os.environ["WP_CATEGORY_FIELD"]
wp_post_id = os.environ.get("WP_POST_ID") or None
with open(os.environ["WP_HTML_PATH"], encoding="utf-8") as f:
    html_body = f.read()

auth = base64.b64encode(f"{WP_USER}:{WP_PASS_CLEAN}".encode()).decode()
payload = {
    "title": title,
    "content": html_body,
    "excerpt": excerpt,
    category_field: [category_id],
}
if wp_post_id:
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/{WP_POST_TYPE}/{wp_post_id}"
    mode = "update"
else:
    payload["status"] = "draft"
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/{WP_POST_TYPE}"
    mode = "create"

req = urllib.request.Request(
    endpoint,
    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    headers={
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json; charset=utf-8",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode())
        status = resp.status
except urllib.error.HTTPError as e:
    print("HTTP_ERROR", e.code, e.read().decode(), flush=True)
    raise SystemExit(1)
print("STATUS", status)
print("MODE", mode)
print("ID", body.get("id"))
print("LINK", body.get("link"))
PY
```

レスポンスのHTTPステータスコードを確認する：

| ステータス | 新規 | 更新 | 対応 |
|---|---|---|---|
| 200 | - | 成功 | `id` フィールドからWP管理画面URLを組み立てて報告 |
| 201 | 成功 | - | `id` フィールドからWP管理画面URLを組み立てて報告。さらにフロントマターに `wp_post_id: {id}` を追記する |
| 401 | 認証エラー | 認証エラー | `.env` の `WP_USER` / `WP_APP_PASS` を確認するよう案内 |
| 404 | エンドポイントエラー | post_idが存在しない | 新規: `WP_POST_TYPE` を確認 / 更新: `wp_post_id` の値を確認 |

WP管理画面URLは `{WP_SITE_URL}/wp-admin/post.php?post={id}&action=edit` で組み立てる。

---

## Step 6 (新規作成時のみ): フロントマターに wp_post_id を追記

新規作成が成功（201）した場合、レスポンスの `id` を `drafts/{filename}` のフロントマターに自動追記する。これにより次回以降の article-post 実行で更新モードに切り替わる。

`Edit` ツールで `category_field: "..."` の直後に以下を挿入する：

```
wp_post_id: {id}
```

挿入後、ユーザーに「次回以降の article-post {filename} は更新モードで動作します」と伝える。

---

## 完了報告

### 新規作成時

```
モード        : 新規作成
記事タイトル  : {title}
カテゴリ      : {category_name}（ID: {category_id}）
WP下書きURL   : {WP管理画面のedit URL}
wp_post_id    : {id}（フロントマターに追記済み）

アイキャッチ用プロンプト:
{eyecatch_prompt}
```

### 更新時

```
モード        : 更新
記事タイトル  : {title}
wp_post_id    : {wp_post_id}
WP編集URL     : {WP管理画面のedit URL}
```

---

## 注意事項

- **投稿前チェック（中立性）**：MD本文・`title`・`excerpt`・関連用語に特定企業名（OPENLOGI 等）やその企業固有の物流・EC 文脈が混ざっていないかを投稿前に確認する。混ざっていれば中立的な一般表現に直してから投稿する。UX TIMES は外部向けの一般記事のため、ユーザー個人設定の「会社名は OPENLOGI 表記」ルールはここでは適用しない（例外）。
- WebSearch / WebFetch（または mcp__workspace__web_fetch）/ mcp__cowork__request_cowork_directory が deferred ツールの場合は `ToolSearch` で先にロードする
- 401 / 404 などのエラーが返った場合は、ユーザーに次のアクションを案内し、勝手にリトライを繰り返さない
- ステップ間で生成した中間ファイル（`/tmp/article_html.txt` 等）は Bash セッションをまたがないため、Step 3〜5 は同じ流れでまとめて実行する
- 既存記事の更新では原則 WordPress を正とする。アイキャッチ差し替えなど一部だけ変えるなら `scripts/upload_eyecatch.py`（本文不変）を使い、`post_to_wp.py` の全体上書きはローカルMDが最新だと確信できるときに限る

---

## 追記：公開後にWP側で直接編集された場合の更新（reconcile）（2026-06 セッション反映）

公開済み記事を、WP管理画面で直接編集したあとに直したいときは、**ローカルMDからの再投稿（post_to_wp.py）で上書きしない**。顔写真・タイトル・画像差し替え等のWP編集を消してしまうため。手順：
1. ローカルの Python（Desktop Commander）で WP REST から対象記事の `content.raw` を取得する（サンドボックスからは叩かない）。
2. 必要な修正だけを文字列置換で当てる（最小差分。他は完全保持）。
3. 同じく REST の POST で `content`（必要なら `excerpt` 等）だけ更新する。`status` は変えない。
4. 取得した最新内容を `drafts/{file}.md` にも書き戻し、MDをWP実体に同期する（今後の編集起点をMDに戻す）。
