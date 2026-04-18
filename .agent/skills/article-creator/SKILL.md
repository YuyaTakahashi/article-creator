---
name: article-creator
description: UX用語の解説記事をWeb検索→執筆→ファクトチェック→WordPress下書き投稿まで一気通貫で実行するスキル。
---

# article-creator スキル

指定されたUX用語の解説記事を生成し、WordPressに下書きとして投稿する。

## 引数

```
/article-creator <topic> [context="..."] [difficulty=0.5] [it=0.5]
```

| 引数 | 必須 | 説明 |
|---|---|---|
| `topic` | 必須 | 記事にするUX用語（例: `メンタルモデル`） |
| `context` | 任意 | 同名異義の場合などに文脈を補足 |
| `difficulty` | 任意 | 記事の難易度 0.0（中学生）〜 1.0（専門教授）、default 0.5 |
| `it` | 任意 | ITリテラシー前提 0.0（一般ユーザー）〜 1.0（熟練エンジニア）、default 0.5 |

---

## 事前設定（初回のみ）

リポジトリルートにある `.env.example` をコピーして `.env` を作成し、値を入力する。

```bash
cp .env.example .env
```

```
WP_SITE_URL=https://your-site.com
WP_USER=your-wordpress-username
WP_APP_PASS=xxxx xxxx xxxx xxxx xxxx xxxx
WP_POST_TYPE=posts
```

`WP_APP_PASS` はWordPress管理画面の「ユーザー → プロフィール → アプリケーションパスワード」で発行する。

---

## 実行手順

### Step 0: リポジトリルートの特定と設定読み込み

以下のBashコマンドで、このスキルのルートディレクトリを特定する。
シンボリックリンク経由か直接コピーかを自動判別する。

```bash
CMD_FILE=~/.claude/commands/article-creator.md
if [ -L "$CMD_FILE" ]; then
  # シンボリックリンクの場合: リンク先からリポジトリルートを逆引き
  SKILL_DIR=$(dirname "$(readlink "$CMD_FILE")")
  REPO_ROOT=$(cd "$SKILL_DIR/../../.."; pwd)
else
  # 直接コピーの場合: ~/.claude/article-creator/ を使用
  REPO_ROOT="$HOME/.claude/article-creator"
fi
echo "REPO_ROOT: $REPO_ROOT"
```

取得した `REPO_ROOT` を以降のすべてのパスのベースとして使用する：
- `.env` は `$REPO_ROOT/.env`
- プロンプトは `$REPO_ROOT/prompts/`

`.env` が存在しない、または必須キーが空の場合はユーザーに作成を促して中断する。

`.env` から以下を読み込む（`WP_POST_TYPE` 未設定時は `posts` をデフォルト値とする）：

```bash
source "$REPO_ROOT/.env"
WP_PASS_CLEAN=$(echo "$WP_APP_PASS" | tr -d ' ')
WP_AUTH=$(echo -n "${WP_USER}:${WP_PASS_CLEAN}" | base64)
```

続いて、WP REST API でその投稿タイプに紐づくカテゴリのタクソノミーフィールド名を取得する。
`posts` の場合は `categories`、カスタム投稿タイプ（例: `glossary`）は独自のタクソノミー名（例: `glossary-category`）を持つことがある。

```python
import urllib.request, json, base64

wp_auth = base64.b64encode(f"{WP_USER}:{WP_PASS_CLEAN}".encode()).decode()

# 既存投稿1件を取得してカテゴリ系フィールド名を調べる
req = urllib.request.Request(
    f"{WP_SITE_URL}/wp-json/wp/v2/{WP_POST_TYPE}?per_page=1",
    headers={"Authorization": f"Basic {wp_auth}"}
)
with urllib.request.urlopen(req) as resp:
    posts = json.loads(resp.read().decode())

# 'categor' を含むキーを探す（例: categories, glossary-category）
CATEGORY_FIELD = "categories"  # デフォルト
if posts:
    for key in posts[0].keys():
        if "categ" in key.lower():
            CATEGORY_FIELD = key
            break
```

以降のステップでは `CATEGORY_FIELD` をカテゴリフィールド名として使用する。

---

### Step 1: 重複チェック

WP REST APIで同名記事の存在を確認する。

```bash
curl -s \
  "${WP_SITE_URL}/wp-json/wp/v2/${WP_POST_TYPE}?search=<topic>&per_page=5&status=publish,draft" \
  -H "Authorization: Basic ${WP_AUTH}"
```

既存記事が見つかった場合はタイトルとURLを表示し、続行するか確認を求める。

---

### Step 2: 情報収集

`$REPO_ROOT/prompts/01_information_gathering.md` を Read ツールで読み込む。
ファイル内の以下のプレースホルダーを置換し、その指示に従って WebSearch を実行・記事の初稿を生成する。

| プレースホルダー | 値 |
|---|---|
| `{topic}` | 引数で受け取ったtopic |
| `{context}` | 引数で受け取ったcontext（省略時は空文字） |

---

### Step 3: 整形・リライト

`$REPO_ROOT/prompts/02_polishing.md` を Read ツールで読み込む。
ファイル内の以下のプレースホルダーを置換し、その指示に従ってStep 2の初稿をリライトする。

| プレースホルダー | 値 |
|---|---|
| `{difficulty}` | 引数で受け取ったdifficulty（default 0.5） |
| `{it}` | 引数で受け取ったit（default 0.5） |
| `{draft}` | Step 2で生成した初稿の全文 |

---

### Step 4: ファクトチェックと自動修正

WebSearch を使って以下の事実を検証し、**誤りは自動修正して続行する**。

- 人名の表記・スペル
- 提唱者・提唱年・所属機関
- 数値・統計データ
- 因果関係・歴史的事実の主張

修正した箇所は `[ファクトチェック修正]` としてコンソールに出力する。
修正がない場合は「ファクトチェック: 問題なし」と出力する。

---

### Step 5: メタデータ抽出

記事本文から以下を抽出・生成する。

#### カテゴリID（1つだけ選択）

| カテゴリ | ID |
|---|---|
| ツール・フレームワーク・方法論・分類 | 22 |
| テクノロジー・技術 | 418 |
| デザイン・情報設計 | 347 |
| マーケティング・ビジネス | 358 |
| リサーチ・分析・テスト | 369 |
| 心理学・行動経済学・脳科学 | 21 |
| 思考・マインド・バイアス | 20 |
| 組織・ファシリテーション | 262 |

#### 同義語辞書（JSON形式）

```json
{
  "記事内の単語A": ["単語A", "正式名称A", "EnglishA"],
  "記事内の単語B": ["単語B", "別名B"]
}
```

---

### Step 5-b: アイキャッチ用プロンプト生成

`$REPO_ROOT/prompts/03_eyecatch.md` を Read ツールで読み込む。
以下のプレースホルダーを置換し、その指示に従って画像生成プロンプトを生成する。

| プレースホルダー | 値 |
|---|---|
| `{topic}` | 引数で受け取ったtopic |
| `{article}` | Step 4完了後の記事本文全文 |

生成したプロンプト文字列を変数に保持し、完了報告で出力する（ファイル保存・WP投稿は行わない）。

---

### Step 6: WordPress REST APIへの下書き投稿

#### 6-1: HTML変換処理

`-- wp分割ライン--` を含む行とそれ以前の行（タイトル・最小限の説明）をWP投稿本文から除外する。
以下の変換ルールを適用してMarkdownをHTMLに変換する：

| Markdown | HTML |
|---|---|
| `## 見出し` | `<h2>見出し</h2>` |
| `### 見出し` | `<h3>見出し</h3>` |
| `**太字**` | `<strong>太字</strong>` |
| `*斜体*` | `<em>斜体</em>` |
| `- リスト項目`（先頭スペースあり ` - ` も同様） | `<ul><li>リスト項目</li></ul>` |
| 段落（空行区切り） | `<p>...</p>` |
| `[A-Za-z.]+¥カタカナ¥` | `<ruby>英字<rt>カタカナ</rt></ruby>` |

リスト行の判定は `line.strip().startswith('- ')` で行い、先頭スペースを無視すること。

---

#### 6-2: 提唱者の顔画像挿入

**人物名の抽出**

HTML変換後の `<h2>語源・提唱者</h2>` セクション内のテキストから、英語で記載されている人物名（`<ruby>` タグ内の英語部分）を抽出する。抽出結果はJSON配列で管理する。

例: `["Louis Pouzin", "Glenda Schroeder", "Ken Thompson", "Stephen Bourne"]`

**各人物のポートレート検索（優先順位順）**

各人物について以下の手順で画像URLを探す。

- WebSearch で `"{person_name}" site:en.wikipedia.org` を検索してWikipedia記事URLを特定する
- WebFetch でそのWikipedia記事を取得し、`upload.wikimedia.org` で始まるポートレート画像URLを抽出する
- Wikimediaで見つからない場合は、`"{person_name}" portrait photo` で再検索し、信頼できるソースの画像URLを探す
- 適切な画像が見つからない場合は `None` として記録してスキップする

選定禁止: 図解・グラフ・ロゴ・風景。顔写真（ポートレート）のみ選ぶ。

**画像HTMLの生成**

```html
<figure><img src="{image_url}" alt="{name_katakana}"><figcaption>{name_katakana}（出典：{image_url}）</figcaption></figure>
```

**挿入位置**

その人物名（英語）が `<ruby>` タグで最初に登場する `</p>` の直後に挿入する。
見つからない場合は `<h2>語源・提唱者</h2>` の直後に挿入する。

---

#### 6-3: WP REST APIへのPOST

```bash
curl -s -X POST \
  "${WP_SITE_URL}/wp-json/wp/v2/${WP_POST_TYPE}" \
  -H "Authorization: Basic ${WP_AUTH}" \
  -H "Content-Type: application/json" \
  -d @- <<'PAYLOAD'
{
  "title": "{topic}（{英語名}）",
  "content": "{HTML変換後の本文}",
  "excerpt": "{最小限の説明}",
  "status": "draft",
  "{CATEGORY_FIELD}": [{category_id}]
}
PAYLOAD
```

レスポンスのHTTPステータスコードを確認する：
- 201: 成功 → `link` フィールドからURL取得して報告
- 401: 認証エラー → `.env` の `WP_USER` / `WP_APP_PASS` を確認するよう案内
- 404: エンドポイントエラー → `WP_POST_TYPE` が正しいか確認するよう案内

---

## 完了報告

```
記事タイトル         : {topic}（{英語名}）
カテゴリ             : {カテゴリ名}（ID: {ID}）
ファクトチェック修正 : {修正箇所のサマリー or "なし"}
WP下書きURL          : {WP管理画面のURL}

アイキャッチ用プロンプト:
{Step 5-bで生成したプロンプト文字列}
```
