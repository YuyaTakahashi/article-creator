---
name: article-post
description: drafts/ フォルダのMDファイルをWordPressに下書き投稿するスキル。article-creator で生成したMDを人間が確認・編集したあとに呼び出す。
---

# article-post スキル

`drafts/` フォルダに保存されたMDファイルを読み込み、HTMLに変換してWordPressに下書きとして投稿する。

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

| フィールド | 用途 |
|---|---|
| `title` | WP投稿タイトル |
| `excerpt` | WP投稿抜粋 |
| `category_id` | カテゴリID |
| `category_field` | タクソノミーフィールド名（例: `glossary-category`） |
| `eyecatch_prompt` | 完了報告に出力（WP投稿には使わない） |

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

```python
import urllib.request, json, base64

wp_auth = base64.b64encode(f"{WP_USER}:{WP_PASS_CLEAN}".encode()).decode()

payload = {
    "title": title,           # フロントマターから取得
    "content": html_body,     # Step 2-3 で生成したHTML
    "excerpt": excerpt,       # フロントマターから取得
    "status": "draft",
    category_field: [category_id]   # フロントマターの category_field と category_id を使用
}

req = urllib.request.Request(
    f"{WP_SITE_URL}/wp-json/wp/v2/{WP_POST_TYPE}",
    data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
    headers={
        "Authorization": f"Basic {wp_auth}",
        "Content-Type": "application/json; charset=utf-8"
    },
    method="POST"
)
```

レスポンスのHTTPステータスコードを確認する：
- 201: 成功 → `id` フィールドからWP管理画面URLを組み立てて報告
- 401: 認証エラー → `.env` の `WP_USER` / `WP_APP_PASS` を確認するよう案内
- 404: エンドポイントエラー → `WP_POST_TYPE` が正しいか確認するよう案内

---

## 完了報告

```
記事タイトル  : {title}
カテゴリ      : {category_name}（ID: {category_id}）
WP下書きURL   : {WP管理画面のedit URL}

アイキャッチ用プロンプト:
{eyecatch_prompt}
```
