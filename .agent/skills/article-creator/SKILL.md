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

以下のBashコマンドで、このスキルが置かれているリポジトリのルートを特定する。

```bash
SKILL_DIR=$(dirname "$(readlink ~/.claude/commands/article-creator.md)")
REPO_ROOT=$(cd "$SKILL_DIR/../../.."; pwd)
echo "$REPO_ROOT"
```

取得した `REPO_ROOT` を以降のすべてのパスのベースとして使用する：
- `.env` は `$REPO_ROOT/.env`
- プロンプトは `$REPO_ROOT/prompts/`
- 下書き保存先は `$REPO_ROOT/drafts/<topic>.md`

`.env` が存在しない、または必須キーが空の場合はユーザーに作成を促して中断する。

`.env` から以下を読み込む（`WP_POST_TYPE` 未設定時は `posts` をデフォルト値とする）：

```bash
source "$REPO_ROOT/.env"
WP_PASS_CLEAN=$(echo "$WP_APP_PASS" | tr -d ' ')
WP_AUTH=$(echo -n "${WP_USER}:${WP_PASS_CLEAN}" | base64)
```

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

### Step 6: ローカルMDファイル保存

`$REPO_ROOT/drafts/{topic}.md` に保存する。

ファイル構成：

```markdown
---
topic: {topic}
en_title: {英語名}
category_id: {ID}
synonyms: {同義語JSONのインライン表記}
---

{Step 4完了後の記事本文（Markdown）}
```

---

### Step 7: WordPress REST APIへの下書き投稿

#### HTML変換処理

`-- wp分割ライン--` を含む行とそれ以前の行（タイトル・最小限の説明）をWP投稿本文から除外する。
以下の変換ルールを適用してMarkdownをHTMLに変換する：

| Markdown | HTML |
|---|---|
| `## 見出し` | `<h2>見出し</h2>` |
| `### 見出し` | `<h3>見出し</h3>` |
| `**太字**` | `<strong>太字</strong>` |
| `*斜体*` | `<em>斜体</em>` |
| `- リスト項目` | `<ul><li>リスト項目</li></ul>` |
| 段落（空行区切り） | `<p>...</p>` |
| `Text¥カタカナ¥` | `<ruby>Text<rt>カタカナ</rt></ruby>` |

#### WP REST APIへのPOST

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
  "categories": [{category_id}]
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
ローカルMD           : drafts/{topic}.md
WP下書きURL          : {WP管理画面のURL}
```
