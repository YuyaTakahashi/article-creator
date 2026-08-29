# article-creator

UX用語の解説記事を生成してWordPressに下書き投稿するClaude Codeスキル。

Web検索 → 執筆 → ファクトチェック → 提唱者ポートレート挿入 → WordPress下書き投稿まで一気通貫で実行する。

---

## 用語集パイプラインの使い方（用語くん・スタッフ向け）

UX TIMES 用語集（uxdaystokyo.com/articles/glossary/）は、Slackの「用語くん」＋用語DB（スプレッドシート）＋記事ドラフト（Googleドキュメント）＋WordPress で回している。まずSlackの `#用語くん` チャンネルで用語くんにメンションするのが入口。

### よく使うリンク

- 用語DB（スプレッドシート・閲覧可）: https://docs.google.com/spreadsheets/d/1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY/edit
- 記事ドラフトフォルダ（Googleドキュメント・閲覧可）: https://drive.google.com/drive/folders/1tQU3-ts3mU6YusLFjijNDNGzdcf-y-GS
- このリポジトリ（Claude Codeで使う人向け）: https://github.com/YuyaTakahashi/article-creator

### 全体の流れ（①〜⑥）

| 手順 | やること | 誰が・どうやるか |
|---|---|---|
| ① 追加 | 用語を候補に積む | 誰でも：Slackで `@用語くん ◯◯ 追加して` |
| ② 生成 | 記事ドラフトを作る | 自動（毎週月曜の朝に3本）／`@用語くん ◯◯ の下書き作って` でリクエスト → 月曜（毎週）か金曜（リクエストがある時）に生成して、チャンネルで告知 |
| ③ レビュー | ドラフトを直す | 誰でも：Googleドキュメントを直接編集 → 用語DBのステータスを「公開OK」に |
| ④ WP下書き | WordPressに下書き化 | 誰でも：`@用語くん G-xxx をWP下書きに`／用語DBメニュー「用語くん」→「▶ 選択行をWP下書きに送る」 |
| ⑤ 画像 | 顔写真＋アイキャッチ＋挿絵 | Claudeがある人：`/glossary-wp-images G-xxx`／無い人：用語DBのR列「アイキャッチプロンプト」をChatGPT・Geminiに渡して作り、WP管理画面で貼る（画像は任意） |
| ⑥ 公開 | 公開する | 誰でも：WP管理画面で「公開」ボタン |
| ⑦ 作り直し | 古い書き方の記事を書き直す | 誰でも：`@用語くん ◯◯ を最新版で作り直して` → 月／金の生成タイミングで最新レシピの新しいDocができる |

### Claude Code を持っている人（Yuya など）

- 単発で今すぐ1本生成：`bash scripts/generate-term.sh "◯◯"` または `/generate-term ◯◯`
- Slackで頼まれた分を今すぐ消化：`bash scripts/friday-glossary-batch.sh --quiet`（新規リクエストと作り直しをまとめて処理。`--quiet` を付けるとSlack告知を出さない。告知は月曜レポートがまとめて出す）
- 画像入れ：`/glossary-wp-images G-xxx`（提唱者の顔写真・アイキャッチ・各章の挿絵を自動でWP下書きに入れる）
- セットアップは下の「セットアップ」を参照。

### Claude Code が無い人

- 記事は自分で書かなくてOK。`@用語くん ◯◯ の下書き作って`（または `@用語くん G-xxx 生成して`）でリクエストすれば、月／金の生成タイミングで作られてチャンネルで知らせが来る。
- 画像を入れたいときは、用語DBのR列「アイキャッチプロンプト」をコピーしてChatGPTやGeminiに渡して画像を作り、WP管理画面（ブロックエディタ）で貼る。顔写真はWikipediaから。画像は無しのまま公開してもOK。

---

## セットアップ（最速）

Claude Codeに以下をそのまま貼り付けるだけでインストールできる。

```
以下のClaude Codeスキルをセットアップして。
https://github.com/YuyaTakahashi/article-creator

手順：
1. リポジトリを git clone する
2. ~/.claude/article-creator/ を作成し prompts/ と .env をそこに置く
3. SKILL.md を ~/.claude/commands/article-creator.md に直接コピーする
4. WordPress の接続情報（WP_SITE_URL / WP_USER / WP_APP_PASS / WP_POST_TYPE）を聞いて .env に書く
```

Claudeがクローン・ファイル配置・`.env`の設定まで対話しながら完了させてくれる。

---

## 動作イメージ

```
/article-creator メンタルモデル
```

1. Web検索で用語の定義・歴史・活用事例を収集（最低3ソース）
2. difficulty / it パラメータに合わせて記事を整形
3. ファクトチェック（誤りは自動修正）
4. 語源・提唱者セクションに顔写真をWikipediaから挿入
5. WordPressに下書きとして投稿 → 編集URLを報告

## 必要なもの

- [Claude Code](https://docs.anthropic.com/ja/docs/claude-code) がインストール済みであること
- WordPress サイト（REST API が有効）
- WordPress のアプリケーションパスワード（管理画面 → ユーザー → プロフィール → アプリケーションパスワードで発行）

## セットアップ

インストール方法は2通りある。どちらでも動作する。

---

### 方法A: シンボリックリンク（リポジトリをgit管理したい場合）

```bash
# 1. クローン
git clone https://github.com/YuyaTakahashi/article-creator.git
cd article-creator

# 2. 認証情報を設定
cp .env.example .env
# .env を開いて WP_SITE_URL / WP_USER / WP_APP_PASS を入力

# 3. シンボリックリンクを作成
ln -s "$(pwd)/.agent/skills/article-creator/SKILL.md" ~/.claude/commands/article-creator.md
```

---

### 方法B: 直接コピー（シンプルに使いたい場合）

```bash
# 1. クローン
git clone https://github.com/YuyaTakahashi/article-creator.git

# 2. ~/.claude/article-creator/ にファイルを配置
mkdir -p ~/.claude/article-creator
cp -r article-creator/prompts ~/.claude/article-creator/
cp article-creator/.env.example ~/.claude/article-creator/.env
# .env を開いて WP_SITE_URL / WP_USER / WP_APP_PASS を入力

# 3. SKILL.md をコマンドディレクトリに直接コピー
cp article-creator/.agent/skills/article-creator/SKILL.md ~/.claude/commands/article-creator.md
```

---

`.env` に入力する値：

```
WP_SITE_URL=https://your-site.com/subdir   # サブディレクトリ構成の場合はパスまで含める
WP_USER=your-wordpress-username
WP_APP_PASS=xxxx xxxx xxxx xxxx xxxx xxxx  # スペース区切りのままでOK
WP_POST_TYPE=glossary                       # 通常の投稿はposts
```

以上でセットアップ完了。

---

### 方法C: Cowork（Claude デスクトップアプリ）から呼び出す

Cowork から「UX用語の記事を作って」のような自然言語でスキルを起動する方法。

Cowork は、マウントされたフォルダ内の `cowork-skills/*/SKILL.md` を自動的にスキルとして認識する。そのため特別なインストール作業は不要で、以下の手順だけで完了する。

```bash
# 1. クローン（未取得の場合のみ）
git clone https://github.com/YuyaTakahashi/article-creator.git
cd article-creator
cp .env.example .env
# .env を開いて WP_SITE_URL / WP_USER / WP_APP_PASS を入力
```

その後 Cowork で本リポジトリのフォルダ（例: `~/workspace/article-creator`）をマウントすれば、`cowork-skills/article-creator/SKILL.md` と `cowork-skills/article-post/SKILL.md` が自動でスキル一覧に登録される。

Cowork での使い方の例：

- 「メンタルモデルの解説記事を書いて」 → `article-creator` が発火し、対話で topic/context/difficulty/it を聞いたあと、drafts/ にMDを保存 → Googleドキュメント化 → 用語DBに「レビュー待ち」で反映する（Step 10）。MDだけ欲しいときは「下書きだけ」と伝える
- 用語DBへの書き戻しはGASのwebhookを叩くため、Coworkのサンドボックスからは届かない（外部HTTPSが403）。スキルは `mcp__Desktop_Commander__start_process` で `scripts/register_draft.py` をユーザーのMac上で実行する。Desktop Commander が繋がっていない場合はコマンドが完了報告に出るので、ターミナルで実行する
- 「drafts/メンタルモデル.md をWordPressに下書き投稿して」 → `article-post` が発火し、WP REST API に POST する

Claude Code 版（方法A / B）と Cowork 版は同じ `prompts/` ・ `.env` ・ `drafts/` を共有するため、どちらから実行しても同じ動作になる。

---

## 使い方

```
/article-creator <topic> [context="..."] [difficulty=0.5] [it=0.5]
```

| 引数 | 必須 | 説明 |
|---|---|---|
| `topic` | 必須 | 記事にするUX用語 |
| `context` | 任意 | 同名異義の場合などに文脈を補足 |
| `difficulty` | 任意 | 難易度 `0.0`（中学生）〜 `1.0`（専門教授）、default `0.5` |
| `it` | 任意 | ITリテラシー前提 `0.0`（一般ユーザー）〜 `1.0`（熟練エンジニア）、default `0.5` |

### 例

```bash
# 基本
/article-creator メンタルモデル

# 文脈を指定
/article-creator "ゴールダイレクテッドデザイン" context="Cooperのデザイン手法として"

# 難易度を下げる
/article-creator UXライティング difficulty=0.3 it=0.2
```

## ファイル構成

```
article-creator/
  .agent/skills/
    article-creator/SKILL.md      # Claude Code スキル本体（下書きMD生成）
    article-post/SKILL.md         # Claude Code スキル本体（WordPress投稿）
  cowork-skills/
    article-creator/SKILL.md      # Cowork 版（下書きMD生成）
    article-post/SKILL.md         # Cowork 版（WordPress投稿）
  prompts/
    01_information_gathering.md   # Web検索・情報収集の指示
    02_polishing.md               # 難易度パラメータ適用・整形の指示
    03_eyecatch.md                # アイキャッチプロンプト生成の指示
  drafts/                         # 生成したMDの保存先
  .env.example                    # 認証情報のテンプレート
  .gitignore
```

## レシピのバージョン管理と記事の作り直し

記事の書き方を決めるプロンプト群（以下「レシピ」）は継続的に直しているため、いつ作った記事かで書きぶりが変わる。どの版で作った記事かを記録して、古い記事を最新の書き方で作り直せるようにしている。

### レシピを直したとき

レシピの構成ファイルは `prompts/recipe-manifest.txt` に列挙されている（`prompts/01_information_gathering.md`・`02_polishing.md`・`03_eyecatch.md`、article-creator と article-review の `SKILL.md`、`CLAUDE.md`）。入れる基準は「直すと記事の中身が変わるか」で、バッチの運用手順や挿絵のスタイルガイドは含めない（含めると書きぶりの同じ記事まで旧版扱いになるため）。どれかを直したら版を上げる。

```bash
python3 scripts/recipe_version.py bump --note "語源セクションを当時の課題起点に変えた"
```

`prompts/VERSION`・`prompts/recipe.lock.json`・`prompts/CHANGELOG.md` が更新される。上げ忘れたまま commit しようとすると pre-commit フックが止める（初回だけ `git config core.hooksPath .githooks` が必要。急ぐときは `git commit --no-verify`）。

| コマンド | 用途 |
|---|---|
| `python3 scripts/recipe_version.py current` | いまの版とハッシュを見る |
| `python3 scripts/recipe_version.py check` | 版の上げ忘れを調べる（ずれていれば exit 1） |
| `python3 scripts/recipe_version.py files` | レシピ構成ファイルと個別ハッシュを一覧する |
| `python3 scripts/stamp_version.py --list` | `drafts/*.md` の版を一覧し、旧版の本数を出す |

版を上げたあと生成バッチが動くと、用語くんがチャンネルに「レシピを v1 → v2 に更新したよ。前の書き方のままの記事が N件」と一報を入れる。

### 記事側の記録

生成時に `scripts/stamp_version.py` がフロントマターへ `creator_version` / `recipe_hash` / `generated_at` を刻み、同じ値が用語DBのS・T列にも入る。バージョン管理を始める前に作った記事は `v0` になっている。

### 作り直しを頼む

Slackで用語くんに頼む。

```
@用語くん モーダル を最新版で作り直して
@用語くん 古い記事教えて
```

用語DBのU列に作り直しフラグが立ち、次の生成タイミング（月曜の朝／金曜はリクエストがある時だけ）で最大2件ずつ書き直される。**旧Docは消さず新しいDocを作る**ので、人が旧Docに入れた編集は残る。用語DBのI列が新Docに差し替わり、旧DocのURLは備考(L列)に残る。

公開済みの記事も作り直せるが、WordPressへの反映は自動ではやらない。新しいDocを確認してから `@用語くん ◯◯ をWP下書きに` で反映する（`wp_post_id` があるので公開状態は保たれたまま本文だけ差し替わる）。

すでに最新版で作られている記事に作り直しを頼むと用語くんが止める。それでも作り直したいときは「強制で作り直して」と言う。

---

## 編集差分から執筆ルールを学ぶ

公開された記事は、AIの初稿に人が手を入れたもの。その差分には「いまの執筆ルールで防げていない弱点」が現れる。週次でそれを拾い、レシピの改訂材料として積む。

```bash
bash scripts/weekly-learn-batch.sh
```

1. `collect_edit_gaps.py` が、公開済み（`wp_post_id` あり・用語DBのW列が空）の記事について、初稿と公開版を段落単位で突き合わせ、`logs/gaps/{日付}/{用語}.md` に差分を出す
2. 差分を読んで分類し、**既存ルールで防げたはず**か**ルール自体が無い**かに切り分けて `prompts/learned/observations.md` に積む
3. 未反映の観測が**3本たまったら** `prompts/learned/proposal-{日付}.md` に改訂案が出る
4. 採用したら `prompts/` を直して `recipe_version.py bump` → 旧版の記事が作り直し候補になる

初稿の正本は `drafts/_baseline/{用語}_{版}.md`（`register_draft.py` がDoc化のときに自動で控える）。無い記事は `drafts/{用語}.md` で代用する。

**プロンプトは自動で書き換えない。Slackにも投稿しない。** 言い回しの最終判断は人がする。詳細は [prompts/learned/README.md](prompts/learned/README.md) を参照。

---

## 用語くん(GAS)のデプロイ

`pipeline/glossary-bot/` が用語くん本体（Apps Script プロジェクト）のソース。ここを `main` にマージすると、GitHub Actions（`.github/workflows/deploy-glossary-bot.yml`）が `clasp push` して Apps Script 側へ反映する。手元の Mac から push する必要はない。

Actions タブから手動実行（`workflow_dispatch`）もできる。

### 初回だけ必要な設定

リポジトリの Secrets に `CLASPRC_JSON` を登録する。中身は手元の clasp のトークンそのもの。

```bash
# Mac で（未ログインなら先に clasp login）
cat ~/.clasprc.json | pbcopy
```

コピーしたものを Settings → Secrets and variables → Actions → New repository secret に、名前 `CLASPRC_JSON` で貼る。

### 先に知っておくこと（重要）

- **このリポジトリはパブリック。** Secrets 自体は非公開で、フォークからの PR では読めない（このワークフローは `push`/`workflow_dispatch` のみで動き、`pull_request` では動かさないため）。ただし置くのは Google アカウントのリフレッシュトークンで、Drive と Apps Script への広い権限を持つ。write 権限を持つ人と、ジョブ内で動く依存パッケージからは触れる状態になる。許容できない場合は、この自動デプロイを使わず手元から `clasp push` する。
- **リスクを下げるなら**：用語くんの Apps Script プロジェクトだけを共有した専用の Google アカウントで `clasp login` し、そのトークンを登録する。yuya 個人アカウントのトークンを置かずに済む。
- **トークンが失効したら**：デプロイが認証エラーで落ちる。Mac で `clasp login` をやり直して `CLASPRC_JSON` を登録し直す。

### デプロイが失敗したとき

`認証情報を書き出す` ステップのエラーメッセージが原因を示す。値そのものはログに出さず、分類だけを出す。

| 出るメッセージ | 意味 | 直し方 |
|---|---|---|
| `Secrets に CLASPRC_JSON がありません` | 未登録 | Secrets に登録する |
| `JSONとして不正: SyntaxError / 先頭が波括弧=false` | JSONでないものが入っている（引用符ごと貼った、パスを貼った等） | `cat ~/.clasprc.json` の出力を、引用符を足さずそのまま貼り直す |
| `JSONとして不正: SyntaxError / 先頭が波括弧=true` | 途中で切れている | 全文をコピーし直す |
| `JSONではあるが clasp の認証ファイルの形ではない` | 別のJSONが入っている | `~/.clasprc.json` の中身か確認する |
| `clasp push` で認証エラー | トークンが失効した | Mac で `clasp login` をやり直して登録し直す |

### 仕様メモ

- `clasp push -f` の `-f` は必須。`appsscript.json` に差分があると clasp は上書き確認を出すが、CI は非対話なので確認できず「Skipping push.」と表示して**終了コード0のまま何もせず**終わる。`-f` が無いと「ジョブは緑なのに反映されていない」事故になる。
- clasp のバージョンは `3.4.1` に固定している。上げるときは、先に手元で同じバージョンの `clasp push` を通してから上げる。
- `clasp push` はコードを反映するだけ。月曜レポート（`sendMondayReport`）のような時間主導トリガーは常に最新コードで動くのでこれで足りる。一方 Slack の webhook は Web アプリなので、固定バージョンでデプロイしている場合は反映に別途 `clasp deploy` が要る。

---

## プロンプトのカスタマイズ

`prompts/` 以下のファイルを編集することで記事スタイルを調整できる。`SKILL.md` は触らなくてよい。
編集したら上の「レシピのバージョン管理」に従って版を上げる。

| ファイル | 役割 |
|---|---|
| `01_information_gathering.md` | 情報収集・初稿生成の指示（構成要素・トーンなど） |
| `02_polishing.md` | 整形ルール（見出し規則・文体・リスト形式など） |
