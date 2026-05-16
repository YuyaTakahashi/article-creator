---
name: article-post
description: drafts/ フォルダのMDファイルをWordPressに新規下書き投稿または既存投稿の更新を行うスキル。article-creator で生成したMDを人間が確認・編集したあとに呼び出す。
---

# article-post スキル

`drafts/` フォルダに保存されたMDファイルを読み込み、HTMLに変換してWordPressに投稿する。

- **新規作成モード**: フロントマターに `wp_post_id` が無い場合、新しい下書きをPOSTする
- **更新モード**: フロントマターに `wp_post_id` がある場合、その投稿を更新する

## 引数

```
/article-post <filename>
```

| 引数 | 必須 | 説明 |
|---|---|---|
| `filename` | 必須 | `drafts/` フォルダ内のMDファイル名（例: `プロプライエタリ・テクノロジー.md`） |

---

## 実行手順

### Step 0: リポジトリルートの特定と設定読み込み

以下のBashコマンドで、このスキルのルートディレクトリを特定する。
シンボリックリンク経由か直接コピーかを自動判別する。

```bash
CMD_FILE=~/.claude/commands/article-post.md
if [ -L "$CMD_FILE" ]; then
  SKILL_DIR=$(dirname "$(readlink "$CMD_FILE")")
  REPO_ROOT=$(cd "$SKILL_DIR/../../.."; pwd)
else
  REPO_ROOT="$HOME/.claude/article-creator"
fi
echo "REPO_ROOT: $REPO_ROOT"
```

`.env` が存在しない、または必須キーが空の場合はユーザーに作成を促して中断する。

`.env` から認証情報を読み込む：

```bash
source "$REPO_ROOT/.env"
WP_PASS_CLEAN=$(echo "$WP_APP_PASS" | tr -d ' ')
```

---

### Step 1: MDファイルの読み込みとパース

`$REPO_ROOT/drafts/{filename}` を Read ツールで読み込む。
ファイルが存在しない場合はエラーを出力して中断する。

YAMLフロントマターから以下を取得する：

| フィールド | 必須 | 用途 |
|---|---|---|
| `title` | ○ | WP投稿タイトル |
| `excerpt` | ○ | WP投稿抜粋 |
| `category_id` | ○ | カテゴリID |
| `category_field` | ○ | タクソノミーフィールド名（例: `glossary-category`） |
| `wp_post_id` | △ | 既存投稿のID。**ある場合は更新モード、無い場合は新規作成モード** |
| `eyecatch_prompt` | - | 完了報告に出力（WP投稿には使わない） |

フロントマター終端（`---` の2行目）以降の全テキストを記事本文として扱う。

---

### Step 2: HTML変換

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

リスト行の判定は `line.strip().startswith('- ')` で行い、先頭スペースを無視すること。
rubyタグの変換は `[A-Za-z0-9.\-]+` で英数字のみにマッチさせ、日本語文字を取り込まないこと。

---

### Step 3: 提唱者の顔画像挿入

**人物名の抽出**

HTML変換後の `<h2>語源・提唱者</h2>` セクション内のテキストから、`<ruby>` タグ内の英語部分（人物名）を抽出する。抽出結果はJSON配列で管理する。

例: `["Louis Pouzin", "Glenda Schroeder", "Ken Thompson"]`

企業名・製品名（Apple, Microsoft, IBM など）は対象外とし、人物名のみを対象とする。

**各人物のポートレート検索（優先順位順）**

- WebSearch で `"{person_name}" site:en.wikipedia.org` を検索してWikipedia記事URLを特定する
- WebFetch でそのWikipedia記事を取得し、`upload.wikimedia.org` で始まるポートレート画像URLを抽出する
- Wikimediaで見つからない場合は `"{person_name}" portrait photo` で再検索する
- 適切な画像が見つからない場合は `None` として記録してスキップする

選定禁止: 図解・グラフ・ロゴ・風景。顔写真（ポートレート）のみ選ぶ。

**画像HTMLの生成と挿入**

```html
<figure><img src="{image_url}" alt="{name_katakana}"><figcaption>{name_katakana}（出典：{image_url}）</figcaption></figure>
```

その人物名（英語）が `<ruby>` タグで最初に登場する `</p>` の直後に挿入する。
見つからない場合は `<h2>語源・提唱者</h2>` の直後に挿入する。

---

### Step 4: WP REST APIへのPOST

フロントマターの `wp_post_id` の有無で、エンドポイントとペイロードを切り替える。

```python
import urllib.request, json, base64

wp_auth = base64.b64encode(f"{WP_USER}:{WP_PASS_CLEAN}".encode()).decode()

# 共通ペイロード
payload = {
    "title": title,
    "content": html_body,
    "excerpt": excerpt,
    category_field: [category_id]
}

if wp_post_id:
    # 更新モード: 既存投稿の status は変更しない（公開済みなら公開のまま、下書きなら下書きのまま）
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/{WP_POST_TYPE}/{wp_post_id}"
    mode = "update"
else:
    # 新規作成モード: status は draft 固定
    payload["status"] = "draft"
    endpoint = f"{WP_SITE_URL}/wp-json/wp/v2/{WP_POST_TYPE}"
    mode = "create"

req = urllib.request.Request(
    endpoint,
    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
    headers={
        "Authorization": f"Basic {wp_auth}",
        "Content-Type": "application/json; charset=utf-8"
    },
    method="POST"
)
```

レスポンスのHTTPステータスコードを確認する：

| ステータス | 新規 | 更新 | 対応 |
|---|---|---|---|
| 200 | - | 成功 | `id` フィールドからWP管理画面URLを組み立てて報告 |
| 201 | 成功 | - | `id` フィールドからWP管理画面URLを組み立てて報告。**さらにフロントマターに `wp_post_id: {id}` を追記するようユーザーに案内する** |
| 401 | 認証エラー | 認証エラー | `.env` の `WP_USER` / `WP_APP_PASS` を確認するよう案内 |
| 404 | エンドポイントエラー | post_idが存在しない | 新規: `WP_POST_TYPE` を確認 / 更新: `wp_post_id` の値を確認 |

---

### Step 5 (新規作成時のみ): フロントマターに wp_post_id を追記

新規作成が成功（201）した場合、レスポンスの `id` を `drafts/{filename}` のフロントマターに自動追記する。
これにより次回以降の `/article-post` 実行で更新モードに切り替わる。

Edit ツールで `category_field: "..."` の直後に以下を挿入する：

```
wp_post_id: {id}
```

挿入後、ユーザーに「次回以降の `/article-post {filename}` は更新モードで動作します」と伝える。

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
