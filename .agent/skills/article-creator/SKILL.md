---
name: article-creator
description: UX用語の解説記事をWeb検索→執筆→ファクトチェック→MDファイル保存まで実行するスキル。WordPress投稿は article-post スキルが担う。
---

# article-creator スキル

指定されたUX用語の解説記事を生成し、`drafts/` フォルダにMDファイルとして保存する。
WordPressへの投稿は、人間がMDを確認・編集したあとに `article-post` スキルで行う。

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

### Step 6: MDファイルへの保存

記事本文・メタデータ・アイキャッチプロンプトをひとつのMDファイルにまとめて `$REPO_ROOT/drafts/` に保存する。

#### ファイル名の決定

topic をファイル名に使えるスラッグに変換する（カタカナ・スペースはハイフン区切りのローマ字で代替してもよいが、日本語のままでも可）。

```
{topic}.md  （例: プロプライエタリ・テクノロジー.md）
```

同名ファイルが既に存在する場合は上書き前にユーザーに確認する。

#### ファイルフォーマット

以下のYAMLフロントマターと本文を組み合わせたMarkdownファイルとして保存する。

```markdown
---
title: "{topic}（{英語名}）"
excerpt: "{最小限の説明}"
category_id: {category_id}
category_name: "{カテゴリ名}"
category_field: "{CATEGORY_FIELD}"
eyecatch_prompt: "{Step 5-bで生成したプロンプト文字列（改行はスペースに置換）}"
---

{-- wp分割ライン-- 以降の記事本文をそのままMarkdownで記載}
```

- フロントマターの値にダブルクォーテーションを含む場合はシングルクォーテーションで囲む
- 記事本文は `-- wp分割ライン--` 行の**次の行から末尾まで**をそのままコピーする（変換・加工しない）

#### 保存後の確認

ファイルが正常に書き込まれたことを確認し、パスを出力する。

---

## 完了報告

```
記事タイトル         : {topic}（{英語名}）
カテゴリ             : {カテゴリ名}（ID: {ID}）
ファクトチェック修正 : {修正箇所のサマリー or "なし"}
保存先              : drafts/{ファイル名}.md

アイキャッチ用プロンプト:
{Step 5-bで生成したプロンプト文字列}

次のステップ: MDを確認・編集したら /article-post {ファイル名}.md を実行してください。
```
