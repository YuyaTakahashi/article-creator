---
name: article-creator
description: |
  UX用語の解説記事をWeb検索→出典台帳つき初稿→整形→台帳と成立条件での照合→MD保存→Googleドキュメント化→用語DB反映まで実行するCoworkスキル。
  WordPress投稿は別スキル article-post が担う。

  以下のリクエストで必ず使用する：
  - 「UX用語の記事を作って」「○○の解説記事をドラフトして」
  - 「メンタルモデルの記事をMDで書いて」「アフォーダンスについて記事化して」
  - 「UX用語集に追加する記事を生成して」「用語解説をWP用に書いて」
  - 「article-creatorで○○を書いて」「/article-creatorしたい」
  Web検索→出典台帳つき初稿→整形→台帳と成立条件での照合→アイキャッチプロンプト生成→drafts/にMD保存→Googleドキュメント化→用語DBへ「レビュー待ち」で反映まで一気通貫で行う。
  「下書きだけ」「MDだけでいい」と言われたときはMD保存で止める。
compatibility: "ユーザーの ~/workspace/article-creator フォルダがマウントされていること、または mcp__cowork__request_cowork_directory で要求可能であること"
---

# article-creator スキル（Cowork版）

指定されたUX用語の解説記事を生成し、`~/workspace/article-creator/drafts/` にMDファイルとして保存したうえで、Googleドキュメント化して用語DB（スプレッドシート）に「レビュー待ち」として反映する（Step 10）。ここまで通すと、Slackの用語くんと月曜レポートが記事の存在を拾えるようになる。
WordPressへの投稿は、人間がDocを確認・編集したあとに `article-post` スキル、または `@用語くん ◯◯ をWP下書きに` で行う。

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

このプロンプトは「出典台帳」「成立条件メモ」「初稿」の3つを出力する。前の2つは次のファイルに保存し、Step 5・Step 6・article-review で使う。

- `research/{topic}_claims.md`（出典台帳。1行1事実で、出典URLと原文の引用を対にしたもの）
- `research/{topic}_conditions.md`（成立条件メモ。用語の種類・成り立つ条件・隣の用語との境界・出典が確かめた範囲・通し例）

台帳の引用は、このセッションで実際に WebFetch で読めたページの文章に限る。403・CAPTCHA などで読めなかった出典は台帳の末尾に記録し、事実の根拠には使わない。

---

## Step 5: 整形・リライト

`/Users/takahashi_yuya/workspace/article-creator/prompts/02_polishing.md` を Read ツールで読み込む。

ファイル内の以下のプレースホルダーを置換し、その指示に従ってStep 4の初稿をリライトする。

| プレースホルダー | 値 |
|---|---|
| `{difficulty}` | Step 1で受け取ったdifficulty（default 0.5） |
| `{it}` | Step 1で受け取ったit（default 0.5） |
| `{draft}` | Step 4で生成した初稿の全文 |
| `{claims}` | `research/{topic}_claims.md` の全文 |
| `{conditions}` | `research/{topic}_conditions.md` の全文 |

---

## Step 5.5: article-critic でレビュー（必須・内部処理）

Step 5 のリライト直後の記事を `article-critic` スキルに渡し、テンプレ準拠 / 文章スタイル / 読み手目線 / 読みやすさ の4軸で採点する。**このスキルを飛ばして Step 6 へ進んではいけない。** 冗長さ・繰り返し・専門語の置き換え漏れを機械的に止める唯一のゲートがここにある。

サイクルは内部処理として扱い、中間のスコアや指摘はユーザーに見せない。ユーザーが見るのは最終的に保存される記事1本だけにする。Critic は「自動リライトのための指示」として使う。

**呼び出しパラメータ:**

```
article_type: ux_glossary
topic: {Step 1で受け取ったtopic}
difficulty: {Step 1で受け取ったdifficulty（default 0.3）}
it: {Step 1で受け取ったit（default 0.3）}
proposed_article: <Step 5 完成稿の全文>
attempt_count: {1回目=1, 2回目=2, 3回目=3}
caller: article-creator (step5.5)
```

**判定の取り扱い:**

- `verdict: regenerate`（1軸でも10点以下） → `regenerate_points` を読み、該当箇所を Step 5 のリライトに戻ってピンポイント修正し、再度 article-critic を呼ぶ。往復は最大2回まで
- `verdict: pass` かつ 12〜14点の軸あり → `regenerate_points` を1回だけ反映してから再度 Critic に通す。トータル3回で打ち切る
- `verdict: pass` かつ改善点なし → Step 6 に進む
- `verdict: escalate`（3回で通過しない、または評価不能） → 「要人間判断」として記録し、**Doc化・用語DB反映には進まない**。この場合に限り Critic の最終ログをユーザーに提示する

**冗長さの扱い（読み手目線Critic）:** 冗長性の指摘が出たら、文をこねて短くするのではなく「その段落を消したとき読者が失う情報は何か」を確かめ、言えない段落を落とす。実務セクションの観点は重要度の低いほうから落としてよい（prompts/02_polishing.md の P4）。

Critic のスコア・指摘は完了報告に出さない。ログJSONは `~/workspace/agentic-solution/AGENT_REPORTS/article-critic-logs/` に残す。

---

## Step 6: 出典台帳と成立条件での照合（関門・省略しない）

article-critic は形式を見るだけで、事実と用語の範囲を見ない。ここで止める。

1. **事実文の照合**：本文の事実を述べる文を1つずつ取り出し、`research/{topic}_claims.md` のどの引用に当たるかを対応づける。人名・年・数値に限らず、提唱者の動機・当時の状況・普及の理由・仕組みの説明・実験の手順と結果も対象にする。
   - 対応する引用が無い文は **削除する**。「〜とされる」でぼかして残さない。
   - 引用が足りないと感じたら、Step 2-4 のソースを `WebFetch` で読み直し、必要なら `WebSearch` で補う。新しく引用を見つけたら台帳に追記してから本文に残す。
   - 仕組みの説明がモデル・仮説なら、事実として言い切らず「〜という考え方では」と誰の説明かが分かる形に直す。見出しも同じ基準で確かめる。
2. **用語の範囲の照合**：`research/{topic}_conditions.md` の成り立つ条件を、リード文の例・各セクションの例・実務の例のすべてに当てる。条件を1つでも満たさない例は隣の用語の例なので、通し例に差し替えるか削る。最小限の説明と定義文に、条件の核が入っているかも確かめる。
3. 修正した箇所は `[照合修正]` としてユーザーに報告する。削除した文と理由（台帳に無い／条件を満たさない）を並べる。修正が無い場合は「照合: 問題なし」と伝える。

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

**選び方（用語が使われる場面でなく、用語の本質で選ぶ）**

- その用語が「何の概念か」で選ぶ。応用先（マーケ・EC・販促など）に引きずられない。
- 説得原理・認知バイアス・心理効果（例: 希少性、社会的証明、アンカリング、ハロー効果、フレーミング）は、販促で使われても本質は心理なので **心理学・行動経済学・脳科学(21)** か **思考・マインド・バイアス(20)** を選ぶ。マーケティング・ビジネス(358)にしない。
  - 21と20の使い分け: 学術的な法則・効果・行動経済学の概念＝21 ／「〜バイアス」「〜効果」で人の判断の歪みを説明する語＝20。迷ったら21。
- **マーケティング・ビジネス(358)** は、事業・販売戦略そのものの用語（ファネル、LTV、ポジショニング、グロースハック、価格戦略など）に限る。
- UIパターン・画面設計＝**デザイン・情報設計(347)** ／ 調査・評価手法や指標＝**リサーチ・分析・テスト(369)** ／ 進め方・合意形成＝**組織・ファシリテーション(262)**。
- 例: 人工的希少性→21（希少性は説得原理）／ ダークパターン→347（UI設計）／ NPS→369（調査指標）／ カスタマージャーニーマップ→347。

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

## Step 8.5: article-critic で最終ゲート（必須・内部処理）

Step 6 の照合修正と Step 7 のメタデータ追加で本文が変わっているため、**保存直前の最終稿をもう一度 `article-critic` に通す**。Step 5.5 と同じく内部で完結させ、中間出力はしない。

**呼び出しパラメータ:**

```
article_type: ux_glossary
topic: {Step 1で受け取ったtopic}
difficulty: {Step 1で受け取ったdifficulty（default 0.3）}
it: {Step 1で受け取ったit（default 0.3）}
proposed_article: <保存直前の最終稿の全文>
attempt_count: final
caller: article-creator (final-gate)
```

判定の処理は Step 5.5 と同じルールに従う。`escalate` のときだけユーザーに見せ、Doc化・用語DB反映には進まない。

**このゲートを通していない記事を保存しない。** 通したかどうかは `article-critic-logs/` にログが残るかで後から確かめられる（`scripts/register_draft.py` が当日ログの有無を確認して警告を出す）。

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
- **`reviewed_at` はここで書かない。** これは `article-review` を実際に通した証跡であり、`scripts/mark_reviewed.py` だけが刻む。生成段で自分で書き足すと、推敲していない記事が投稿ゲートを通ってしまう

### レシピ版の刻印（保存したら必ず実行する）

このスキルの執筆指示（レシピ）は継続的に直しているため、記事だけ見ると「いつの書き方で書かれたか」が分からなくなる。保存の直後に次を実行し、フロントマターへ `creator_version` / `recipe_hash` / `generated_at` を入れる。外部通信を伴わないので Cowork サンドボックスでも実行できる。

```bash
cd "${REPO_BASH:-$HOME/workspace/article-creator}" && python3 scripts/stamp_version.py "drafts/{ファイル名}.md"
```

`REPO_BASH` は Cowork のとき Step 0-1 で解決したマウント先が入る。Claude Code のときは未設定なので `~/workspace/article-creator` にフォールバックする。

**必ずファイル名を指定して実行する。`--backfill` は使わない。** `--backfill` はバージョン管理を始める前の記事を一括で `v0` にする移行専用で、いま生成した記事に当てると最新レシピで書いたのに `v0` が刻まれ、その記事が最初から作り直し対象になってしまう。

古い版の記事を書き直したときは、元の版を添える：`python3 scripts/stamp_version.py "drafts/{ファイル名}.md" --regenerated-from v2`

刻んだ `creator_version` は用語DBのS列にも入り、Slackの用語くんが「この記事は旧版だから作り直す？」と判断する材料になる。何らかの理由で実行できなかったときは、完了報告にこのコマンドを載せてユーザーに実行してもらう。

### 本文の記法ルール（必ず守る）

中身の書き方は `prompts/02_polishing.md` の執筆原則 P1〜P7 を唯一の正とする（ここに再掲しない）。保存の直前に、次の体裁だけを確かめる。

- **タイトル**：原則、**日本語呼称のみ**にする（CLAUDE.md F2）。日本語呼称が定着していない英語句・略語の用語に限り「略語（英語フルネーム）」形式にする（例: `HMW（How Might We）`）。
- **人名のルビ**：提唱者などの人名は `英字¥カタカナ¥` 形式で書く（CLAUDE.md F1）。姓・名はトークンごとに分けて振る。
- **最小限の説明**：`excerpt` と完全一致、20〜35文字、句点なし、名詞締め（CLAUDE.md F4）。
- **表はスマホ優先**：比較・対応表は「**区分（ラベル）を左列・内容を右列**」の **2列・1項目1行** で書く。
- **画像**：挿絵は `drafts/images/{slug}/{内容を表す名前}.png`（連番を付けない）、アイキャッチは `eyecatch_image:` にローカルパスで置く。挿絵は Step 6 の照合を終えた本文の通し例から作り、成立条件を満たす場面を描く（pipeline/batch-instructions.md Step 3.5）。

書き込みは Write ツールで行う。完了したら `present_files` でユーザーに直接見せる。

---

## Step 10: 用語DBへの反映（Doc化 → 書き戻し）

`drafts/` に保存しただけでは用語DB（Googleスプレッドシート）は更新されず、Slackの用語くんも月曜レポートも記事の存在を知らない。ここまで通して初めて「下書きができた」状態になる。

次のときはこのステップを飛ばす。

- ユーザーが「下書きだけ」「MDだけでいい」「途中まででいい」と言った場合
- 無人モード（月曜・金曜の生成バッチ）から呼ばれた場合。バッチは自分でDoc化と書き戻しを行う

### 10-1. レビュー用MDを組み立てる

手で組み立てず、次のスクリプトに作らせる。フロントマターの除去・タイトル行・レビュー案内行・**レシピ版の行**をまとめて付ける。

```bash
cd "${REPO_BASH:-$HOME/workspace/article-creator}" && python3 scripts/make_doc_md.py "drafts/{ファイル名}.md"
# 古い版を作り直したときは: --old-doc-url "{旧DocURL}"
```

`pipeline/doc-ready/{ファイル名}.md` に、次の形で書き出される。

```
# {タイトル}

*（レビュー用ドラフト：本文を直接編集してください。英字¥カタカナ¥ は読みがな記法、-- wp分割ライン-- は投稿時の区切りマーカーなので、そのまま残してください）*

*（版：v15 ／ レシピhash 7fe2c26a0557 ／ 生成日 2026-09-07 ／ この行はレビュー用で、WordPressには載りません）*
```

版の行は、レビューする人がDocだけを見て「どのレシピ版で書かれた記事か」を判断できるようにするためのもの。手で消さない。「レシピ版の刻印」を飛ばしているとスクリプトが止まるので、止まったら stamp_version.py をやり直す。

### 10-2. Googleドキュメントにする

10-1 が書き出したMDの中身をそのまま渡し、Drive連携の `create_file` で作る（Cowork・Claude Code のどちらでも動く）。

- `contentMimeType`: `text/markdown`（これでGoogleドキュメントに自動変換される）
- `parentId`: `1tQU3-ts3mU6YusLFjijNDNGzdcf-y-GS`（記事ドラフトフォルダ）
- `name`: 用語名

作り直しのときは**旧Docを消さず新しいDocを作る**。人が旧Docに入れた編集を残すため。作成されたDocのURLを控える。

### 10-3. 用語DBに書き戻す

```bash
cd "${REPO_BASH:-$HOME/workspace/article-creator}" && python3 scripts/register_draft.py "drafts/{ファイル名}.md" --doc-url "{10-2のDocURL}"
```

作り直しのときは元の版と旧Docを添える：`--regenerated-from v0 --old-doc-url "{旧DocURL}"`

このスクリプトがフロントマターを読み、用語DBのB列から行を探し（無ければ新しい行を作り）、ステータス・Docリンク・slug・excerpt・category_id・アイキャッチプロンプト・レシピ版をまとめて書き戻す。送る前に中身を確かめたいときは `--dry-run` を付ける。

**Coworkのサンドボックスからは実行できない**（GASのwebhookが外部HTTPSで403になる）。Cowork では `mcp__Desktop_Commander__start_process` でこのコマンドを実行する。ユーザーのMac上で直接動くのでローカル実行にあたり、サンドボックス禁止ルールには反しない。Desktop Commander が使えないときは、コマンドをそのまま完了報告に載せてユーザーに実行してもらう。黙って飛ばさない。

---

## 完了報告

```
記事タイトル         : {topic}
カテゴリ             : {カテゴリ名}（ID: {ID}）
照合修正       : {削除・差し替えした文と理由のサマリー or "なし"}
保存先              : drafts/{ファイル名}.md
レシピ版             : {creator_version}（{recipe_hash}）
用語DB              : {G-ID} / {ステータス} / {DocのURL}　※Step 10を飛ばした場合は「未反映（下書きのみ）」

アイキャッチ用プロンプト:
{Step 8で生成したプロンプト文字列}

次のステップ:
- WordPressに直接投稿する場合: MDを確認・編集したあと「article-post でこのMDをWordPressに投稿して」と依頼する。
- 用語DBパイプライン（Doc化 → 用語DBに「レビュー待ち」として反映 → 月曜レポートに掲載）まで一気にやる場合: ローカルで `bash scripts/generate-term.sh "{topic}"` を実行する。内部でこの article-creator を呼び、続けて Doc化（記事ドラフトフォルダ）と update_row（用語DB書き戻し）を行う（Doc化・webhookは外部HTTPSのためローカル専用。Coworkサンドボックスでは実行しない）。
```

---

## 注意事項

- WebSearch / WebFetch / mcp__cowork__request_cowork_directory / mcp__cowork__present_files / Skill が deferred ツールの場合は `ToolSearch` で先にロードする
- ユーザーが「途中まででいい」「ドラフトだけ見たい」と言った場合は Step 9 までで止めて投稿には進まない
- 日本語の表記ルール（「である」調、体言止め禁止、受動態回避）は prompts/02_polishing.md の指示に従う
- **外部公開記事の中立性**：本文・タイトル・excerpt・関連用語に特定企業名（OPENLOGI 等）やその企業固有の物流・EC 文脈を入れない。用語は中立的な一般解説として書く（詳細は prompts/02_polishing.md 執筆ルール6・CLAUDE.md 記事の書き方ルール6）
- Step 2 のディープリサーチは Chrome / NotebookLM への依存が大きいため、失敗時は 2-5 のフォールバックに従って静かに WebSearch ベースに切り替える


