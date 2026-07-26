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

### Claude Code を持っている人（Yuya など）

- 単発で今すぐ1本生成：`bash scripts/generate-term.sh "◯◯"` または `/generate-term ◯◯`
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

- 「メンタルモデルの解説記事を書いて」 → `article-creator` が発火し、対話で topic/context/difficulty/it を聞いてから drafts/ にMDを保存する
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

## プロンプトのカスタマイズ

`prompts/` 以下のファイルを編集することで記事スタイルを調整できる。`SKILL.md` は触らなくてよい。

| ファイル | 役割 |
|---|---|
| `01_information_gathering.md` | 情報収集・初稿生成の指示（構成要素・トーンなど） |
| `02_polishing.md` | 整形ルール（見出し規則・文体・リスト形式など） |
