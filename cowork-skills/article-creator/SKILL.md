---
name: article-creator
description: |
  UX用語の解説記事をWeb検索→執筆→ファクトチェック→MDファイル保存まで実行するCoworkスキル。
  WordPress投稿は別スキル article-post が担う。

  以下のリクエストで必ず使用する：
  - 「UX用語の記事を作って」「○○の解説記事をドラフトして」
  - 「メンタルモデルの記事をMDで書いて」「アフォーダンスについて記事化して」
  - 「UX用語集に追加する記事を生成して」「用語解説をWP用に書いて」
  - 「article-creatorで○○を書いて」「/article-creatorしたい」
  Web検索→初稿→整形→ファクトチェック→アイキャッチプロンプト生成→drafts/にMD保存まで一気通貫で行う。
compatibility: "ユーザーの ~/workspace/article-creator フォルダがマウントされていること、または mcp__cowork__request_cowork_directory で要求可能であること"
---

# article-creator スキル（Cowork版）

指定されたUX用語の解説記事を生成し、`~/workspace/article-creator/drafts/` フォルダにMDファイルとして保存する。
WordPressへの投稿は、人間がMDを確認・編集したあとに `article-post` スキルで行う。

---

## Step 0: リポジトリのマウントと設定読み込み

### 0-1. 作業フォルダの確保

まず `~/workspace/article-creator` がマウント済みかを確認する。

```bash
ls /sessions/*/mnt/article-creator/.env 2>/dev/null && echo "MOUNTED" || echo "NOT_MOUNTED"
```

`NOT_MOUNTED` の場合は `mcp__cowork__request_cowork_directory` を `path="~/workspace/article-creator"` で呼び出し、ユーザーに承認してもらう。

マウント後、Bash上では `/sessions/<session>/mnt/article-creator/` で参照できる。実セッション名を毎回固定するのは避け、以下のように動的に解決する。

```bash
REPO_BASH=$(ls -d /sessions/*/mnt/article-creator 2>/dev/null | head -1)
if [ -z "$REPO_BASH" ]; then
  echo "ERROR: article-creator がマウントされていません" >&2
  exit 1
fi
echo "REPO_BASH=$REPO_BASH"
```

Read/Write/Edit ツールは `/Users/takahashi_yuya/workspace/article-creator/` を使う。BashとRead系でパスが異なる点に注意する。

### 0-2. .env の読み込み

```bash
if [ ! -f "$REPO_BASH/.env" ]; then
  echo "ERROR: $REPO_BASH/.env が存在しません。.env.example をコピーして値を埋めてください" >&2
  exit 1
fi
set -a
source "$REPO_BASH/.env"
set +a
WP_PASS_CLEAN=$(echo "$WP_APP_PASS" | tr -d ' ')
```

必須キー `WP_SITE_URL` / `WP_USER` / `WP_APP_PASS` が空ならエラーメッセージを出して中断する。`WP_POST_TYPE` 未設定時は `posts` をデフォルト値とする。

### 0-3. カテゴリフィールド名の自動判定

WP REST API でその投稿タイプに紐づくカテゴリのタクソノミーフィールド名を取得する。`posts` の場合は `categories`、カスタム投稿タイプ（例: `glossary`）は独自のタクソノミー名（例: `glossary-category`）を持つことがある。

```bash
python3 - <<'PY'
import os, urllib.request, json, base64
WP_SITE_URL = os.environ["WP_SITE_URL"]
WP_USER = os.environ["WP_USER"]
WP_PASS_CLEAN = os.environ["WP_PASS_CLEAN"]
WP_POST_TYPE = os.environ.get("WP_POST_TYPE", "posts")
auth = base64.b64encode(f"{WP_USER}:{WP_PASS_CLEAN}".encode()).decode()
req = urllib.request.Request(
    f"{WP_SITE_URL}/wp-json/wp/v2/{WP_POST_TYPE}?per_page=1",
    headers={"Authorization": f"Basic {auth}"}
)
with urllib.request.urlopen(req) as resp:
    posts = json.loads(resp.read().decode())
category_field = "categories"
if posts:
    for key in posts[0].keys():
        if "categ" in key.lower():
            category_field = key
            break
print(category_field)
PY
```

得られた値を `CATEGORY_FIELD` として以降のステップで使う。

---

## Step 1: 引数を対話で収集

`AskUserQuestion` ツールで1問ずつ聞く。スキル起動時のメッセージに値が含まれていれば該当質問はスキップしてよい。

### 質問1: topic（必須）

```
記事にするUX用語を入力してください。
例: メンタルモデル、ユーザビリティ、アフォーダンス
```

空欄なら再質問する。

### 質問2: context（任意）

```
同名異義語や補足したい文脈があれば入力してください。
（不要な場合は空欄）
```

空欄の場合は `context = ""` として扱う。

### 質問3: difficulty（任意）

```
記事の難易度を 0.0〜1.0 で指定してください。
  0.0 = 中学生レベル
  0.5 = 一般向け（デフォルト）
  1.0 = 専門教授レベル
```

数値以外・範囲外なら 0.5 にフォールバックする。

### 質問4: it（任意）

```
読者のITリテラシーを 0.0〜1.0 で指定してください。
  0.0 = 一般ユーザー
  0.5 = ビジネスパーソン（デフォルト）
  1.0 = 熟練エンジニア
```

数値以外・範囲外なら 0.5 にフォールバックする。

---

## Step 1.5: 既存記事の重複チェック（最初に必ず実行・ハードゲート）

topic 確定の直後、**ディープリサーチ（Step 2）・執筆・画像生成に入る前に**、同じ用語の記事が
既に WordPress に無いかを必ず確認する。リサーチや画像生成はコストが高く、重複記事の二重作成が
最も避けたい失敗なので、ここを最初のゲートにする。

Coworkサンドボックスからは uxdaystokyo.com に到達できない（外部HTTPSが403でブロックされる）。
重複チェックは post_to_wp.py と同様、**ローカル実行（Desktop Commander）** で行う。次を実行する：

```bash
cd ~/workspace/article-creator
python3 scripts/check_duplicate.py "{topic}" "{topic_en}"
```

- 終了コード 0（重複なし）: そのまま Step 2 へ進む。
- 終了コード 2（重複候補あり）: 出力されたタイトル・slug・URL・ステータスを提示し、**新規作成を止めて**
  `AskUserQuestion` で確認する：
    - 中止する（既存記事があるので作らない）← 既定
    - 既存記事を更新する（その id を `wp_post_id` としてフロントマターに入れ、更新前提で進める）
    - それでも別記事として新規作成する（slug 重複に注意）
- 重複が解消するまで Step 2 以降へ進まない。このゲートは省略しない。

---

## Step 2: ディープリサーチ実行（必須・デフォルト）

NotebookLM Deep Research を Chrome 経由で動かし、Web を広範にクロールして信頼できるソース一覧を収集する。実際の処理は別スキル `notebooklm-deep-research` に委譲する。

### 2-1. リサーチプロンプトの組み立て

`topic` と `context` を組み合わせて、NotebookLM に渡すリサーチプロンプトを生成する。海外の一次情報を優先するため、プロンプトは英語で書き、検索範囲も英語圏のソースを中心に指定する。

```
Conduct a comprehensive deep research on '{topic_en}' (Japanese: '{topic}').
Cover: definition, historical background, the original proponent and their affiliation,
core principles, practical application in UX / product design, and concrete case studies.

Prioritize trustworthy English-language primary sources: academic papers, the proponent's
own publications or blog, books, peer-reviewed journals, official documentation from
established design / UX institutions (e.g. Nielsen Norman Group, IDEO, IxDA, ACM, IEEE),
and major English-language professional media. Japanese sources may be added only as
supplementary references; do not rely on them as primary evidence.

Context (if any): {context}
```

`{topic_en}` は topic の英語表記。判断がつかない場合は WebSearch で英語名を1回引いてから組み立てる。`context` が空の最後の1行は省略する。

### 2-2. 保存先の指定

リサーチ結果のMDファイルは `/Users/takahashi_yuya/workspace/article-creator/research/` 配下に保存する。`research/` が無ければ事前に作成する。

```bash
mkdir -p "$REPO_BASH/research"
```

ファイル名は `research_{topic_slug}_{YYYYMMDD}.md` 形式。`topic_slug` は日本語のままでもよい。

### 2-3. notebooklm-deep-research スキルの呼び出し

Skill ツールで `notebooklm-deep-research` を呼び出し、以下を引数として伝える：

- リサーチトピック: 2-1 で組み立てたプロンプト
- 保存先: `/Users/takahashi_yuya/workspace/article-creator/research/research_{topic_slug}_{YYYYMMDD}.md`

スキルが完了すると、保存先パスのMDファイルにソース一覧（番号付きリスト形式・タイトル＋URL）が記録される。

### 2-4. ソース一覧の読み込み

保存されたMDファイルを Read ツールで読み込み、「ソース一覧（INDEX）」セクションの番号付きリスト部分を抽出する。抽出した文字列を `{sources}` 変数として保持し、Step 3 のプロンプトに差し込む。

### 2-5. フォールバック

以下のいずれかに該当する場合は、Step 2 を中断して Step 3 以降を従来通り WebSearch ベースで実行する。`{sources}` には `ディープリサーチ未実施: Web検索で補完してください` という1行を入れる。

- Chrome が起動できない、NotebookLM へのログインが必要、Deep Research UI が見つからない
- 10分以上待ってもソース候補が出ない
- ユーザーが明示的に「ディープリサーチは飛ばして」と指示した

中断・スキップした場合は、その理由をユーザーに1行で報告してから次に進む。

---

## Step 3: 重複チェック → Step 1.5 に統合済み

重複チェックは Step 1.5（ディープリサーチ前のハードゲート）で `scripts/check_duplicate.py` を
ローカル実行して済ませる。ここでは何もしない。

---

## Step 4: 情報収集（初稿生成）

`/Users/takahashi_yuya/workspace/article-creator/prompts/01_information_gathering.md` を Read ツールで読み込む。

ファイル内の以下のプレースホルダーを置換し、その指示に従って記事の初稿を生成する。

| プレースホルダー | 値 |
|---|---|
| `{topic}` | Step 1で受け取ったtopic |
| `{context}` | Step 1で受け取ったcontext（省略時は空文字） |
| `{sources}` | Step 2-4で抽出したソース一覧の番号付きリスト全文。ディープリサーチをスキップした場合は `ディープリサーチ未実施: Web検索で補完してください` |

`{sources}` に実ソースがある場合は、各URLに対して `WebFetch`（または `mcp__workspace__web_fetch`）を実行して本文を取得し、そこから事実を引き出して執筆する。`{sources}` が「未実施」表記の場合のみ、従来通り `WebSearch` で独自にソースを集める。

WebSearch / WebFetch ツールが未ロードの場合は `ToolSearch` で先にロードする。

---

## Step 5: 整形・リライト

`/Users/takahashi_yuya/workspace/article-creator/prompts/02_polishing.md` を Read ツールで読み込む。

ファイル内の以下のプレースホルダーを置換し、その指示に従ってStep 4の初稿をリライトする。

| プレースホルダー | 値 |
|---|---|
| `{difficulty}` | Step 1で受け取ったdifficulty（default 0.5） |
| `{it}` | Step 1で受け取ったit（default 0.5） |
| `{draft}` | Step 4で生成した初稿の全文 |

---

## Step 6: ファクトチェックと自動修正

以下の事実を検証し、誤りは自動修正して続行する。

- 人名の表記・スペル
- 提唱者・提唱年・所属機関
- 数値・統計データ
- 因果関係・歴史的事実の主張

検証の優先順位:

1. Step 2-4で取得したソース一覧の各URLを `WebFetch` で再度参照する（ディープリサーチで集めた信頼性の高い一次情報なので、まずこちらから当たる）
2. ソース内に該当事実の記載がない、または曖昧な場合のみ `WebSearch` で追加検証する

修正した箇所は `[ファクトチェック修正]` としてユーザーに報告する。修正がない場合は「ファクトチェック: 問題なし」と伝える。

---

## Step 7: メタデータ抽出

記事本文から以下を抽出・生成する。

### カテゴリID（1つだけ選択）

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

### 同義語辞書（JSON形式）

```json
{
  "記事内の単語A": ["単語A", "正式名称A", "EnglishA"],
  "記事内の単語B": ["単語B", "別名B"]
}
```

---

## Step 8: アイキャッチ用プロンプト生成

`/Users/takahashi_yuya/workspace/article-creator/prompts/03_eyecatch.md` を Read ツールで読み込む。

以下のプレースホルダーを置換し、その指示に従って画像生成プロンプトを生成する。

| プレースホルダー | 値 |
|---|---|
| `{topic}` | Step 1で受け取ったtopic |
| `{article}` | Step 6完了後の記事本文全文 |

生成したプロンプト文字列を変数に保持し、Step 9 のフロントマターに埋め込む。ファイル保存・WP投稿はここでは行わない。

---

## Step 9: MDファイルへの保存

記事本文・メタデータ・アイキャッチプロンプトをひとつのMDファイルにまとめて `/Users/takahashi_yuya/workspace/article-creator/drafts/` に保存する。

### ファイル名の決定

`{topic}.md`（例: `プロプライエタリ・テクノロジー.md`）。日本語のままでよい。

同名ファイルが既に存在する場合は `AskUserQuestion` で上書き確認する。

### ファイルフォーマット

以下のYAMLフロントマターと本文を組み合わせたMarkdownファイルとして保存する。

```markdown
---
title: "{topic}"
excerpt: "{最小限の説明}"
category_id: {category_id}
category_name: "{カテゴリ名}"
category_field: "{CATEGORY_FIELD}"
eyecatch_prompt: "{Step 8で生成したプロンプト文字列（改行はスペースに置換）}"
---

{-- wp分割ライン-- 以降の記事本文をそのままMarkdownで記載}
```

- フロントマターの値にダブルクォーテーションを含む場合はシングルクォーテーションで囲む
- 記事本文は `-- wp分割ライン--` 行の次の行から末尾までをそのままコピーする（変換・加工しない）

### 本文の記法ルール（指摘反映・必ず守る）

- **タイトル**：原則、**日本語呼称のみ**にする（英語名はタイトルに併記しない。英語名は本文の初出で一度だけ示す）。日本語呼称が定着していない英語句・略語の用語に限り「略語（英語フルネーム）」形式にする（例: `HMW（How Might We）`）。
- **人名のルビ**：提唱者などの人名は `英字¥カタカナ¥` 形式で書く（`¥` は半角円記号。`article-post` の `md_to_html` が `<ruby>` に変換する）。例: `Min¥ミン¥ Basadur¥バサドゥール¥`。姓・名はトークンごとに分けて振る。
- **表はスマホ優先**：比較・対応表は「**区分（ラベル）を左列・内容を右列**」の **2列・1項目1行** で書く（横並び3列以上は避け、縦持ちに転置する）。スマホで横に潰れず読める。
- **画像**：挿絵は `drafts/images/{slug}/{内容を表す名前}.png`（連番を付けない）、アイキャッチは `eyecatch_image:` にローカルパスで置く（`article-post` がWPメディアへアップする）。挿絵スタイルは `style-guide-eyecatch.md` の「挿絵スタイル（NotebookLM風／説明図寄り・可愛くしすぎない）」に従う。

書き込みは Write ツールで行う。完了したら `present_files` でユーザーに直接見せる。

---

## 完了報告

```
記事タイトル         : {topic}
カテゴリ             : {カテゴリ名}（ID: {ID}）
ファクトチェック修正 : {修正箇所のサマリー or "なし"}
保存先              : drafts/{ファイル名}.md

アイキャッチ用プロンプト:
{Step 8で生成したプロンプト文字列}

次のステップ: MDを確認・編集したあと「article-post でこのMDをWordPressに投稿して」と依頼してください。
```

---

## 注意事項

- WebSearch / WebFetch / mcp__cowork__request_cowork_directory / mcp__cowork__present_files / Skill が deferred ツールの場合は `ToolSearch` で先にロードする
- ユーザーが「途中まででいい」「ドラフトだけ見たい」と言った場合は Step 9 までで止めて投稿には進まない
- 日本語の表記ルール（「である」調、体言止め禁止、受動態回避）は prompts/02_polishing.md の指示に従う
- **外部公開記事の中立性**：本文・タイトル・excerpt・関連用語に特定企業名（OPENLOGI 等）やその企業固有の物流・EC 文脈を入れない。用語は中立的な一般解説として書く（詳細は prompts/02_polishing.md 執筆ルール6・CLAUDE.md 記事の書き方ルール6）
- Step 2 のディープリサーチは Chrome / NotebookLM への依存が大きいため、失敗時は 2-5 のフォールバックに従って静かに WebSearch ベースに切り替える


