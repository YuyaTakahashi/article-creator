# article-creator

UX用語の解説記事を生成してWordPressに下書き投稿するClaude Codeスキル。

Web検索 → 執筆 → ファクトチェック → 提唱者ポートレート挿入 → WordPress下書き投稿まで一気通貫で実行する。

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
  .agent/skills/article-creator/
    SKILL.md          # スキル本体（ステップ制御）
  prompts/
    01_information_gathering.md   # Web検索・情報収集の指示
    02_polishing.md               # 難易度パラメータ適用・整形の指示
  .env.example        # 認証情報のテンプレート
  .gitignore
```

## プロンプトのカスタマイズ

`prompts/` 以下のファイルを編集することで記事スタイルを調整できる。`SKILL.md` は触らなくてよい。

| ファイル | 役割 |
|---|---|
| `01_information_gathering.md` | 情報収集・初稿生成の指示（構成要素・トーンなど） |
| `02_polishing.md` | 整形ルール（見出し規則・文体・リスト形式など） |
