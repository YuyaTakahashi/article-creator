# article-creator / article-post 作業ルール（厳守）

## WordPress への投稿は必ずローカルの Python で実行する

このリポジトリで WordPress（uxdaystokyo.com）へ投稿・更新するときは、**必ず**ユーザーのローカルターミナルで次のスクリプトを実行する。

```
cd ~/workspace/article-creator
python3 scripts/post_to_wp.py drafts/{ファイル名}.md
```

### 絶対にやってはいけないこと（再発防止）

- Cowork のサンドボックス（`mcp__workspace__bash`）から uxdaystokyo.com へ **一切アクセスしない**。POST だけでなく、GET・疎通確認・カテゴリ/タクソノミーの自動検出・メディアアップロードも全部ローカルの py に任せる。
- サンドボックスから外部 HTTPS は 403 でブロックされる。試すこと自体が無駄なので、接続テストすらしない。
- `web_fetch` で WP REST API を叩いて代用しようとしない。

### Claude がサンドボックスでやってよいこと

- MD の執筆・編集・ファクトチェック
- `drafts/` への MD 配置
- フロントマターの確認・修正（例: `category_field` は `glossary` 投稿タイプでは `glossary-category`）
- ローカル実行コマンドをユーザーに案内する

### 投稿フロー

1. Claude が `drafts/{ファイル名}.md` を整える（フロントマター含む）
2. Claude はローカル実行コマンドをユーザーに渡す（自分では POST しない）
3. ユーザーがローカルで `scripts/post_to_wp.py` を実行する
4. 成功時、スクリプトがフロントマターに `wp_post_id` を追記する（次回は更新モード）

## カテゴリのタクソノミー名

`glossary` 投稿タイプのカテゴリフィールドは `glossary-category` を使う（`categories` ではない）。

## ローカル実行の手段

WordPress への投稿は、サンドボックスではなく **Desktop Commander（`mcp__Desktop_Commander__start_process`）** で実行する。これはユーザーの Mac 上で直接動くため「ローカル実行」に当たり、サンドボックス禁止ルールに反しない。

```
cd ~/workspace/article-creator
python3 scripts/post_to_wp.py drafts/{ファイル名}.md
```

## 記事の書き方ルール（投稿前に必ず守る・再発防止）

UX TIMES は専門家が書いた根拠のある用語集だが、網羅性より読みやすさを優先する媒体である。ただし、事実の正確さと用語の範囲の正しさは、読みやすさより優先する。

ルールは2層に分ける。

- **執筆原則（P1〜P7）**：何をどう書くか。`prompts/02_polishing.md` の「執筆原則」を唯一の正とし、ここには再掲しない。過去の個別の直し（`prompts/learned/observations.md`）は、すべてどれかの原則の具体例にあたる。新しい直しが出たら、原則を増やす前に、どの原則の違反かを考えて「確かめ方」を足す。
  - P1 出典台帳にある事実だけを書く（裏づけの無い文は「〜とされる」でぼかさず削る）
  - P2 用語の範囲（成り立つ条件・隣の用語との境界）を先に決め、定義・例・挿絵をその範囲で確かめる
  - P3 どの文も新しい情報を1つ運ぶ
  - P4 構成の項目は「調べる観点」であって「埋める枠」ではない
  - P5 具体例は1本を記事全体で使い回す
  - P6 初めて読む人の言葉で書く
  - P7 固有の情報は、知ると用語の使い方が変わるものだけ書く
- **形式ルール（F1〜F6）**：機械的に確かめられる体裁。下に書く。

### F1. ルビ（外国人名・外国語の固有名詞）

人名などの外国語は、カタカナ＋括弧英語（例: `ロバート・M・ヤーキズ（Robert M. Yerkes）`）に **しない**。必ずルビ記法 `英字¥カタカナ¥` で書く。py が `<ruby>` に変換する。

- 正: `Robert¥ロバート¥ M.¥エム¥ Yerkes¥ヤーキズ¥`
- 誤: `ロバート・M・ヤーキズ（Robert M. Yerkes）`
- 英単語ごとに `¥カタカナ¥` を付ける。論文名・雑誌名・製品名（Duolingo 等）は対象外でそのまま英語表記にする。

### F2. タイトルに英語を入れない

`title` は日本語のみにする。「日本語 + 英語名」の併記は **しない**。

- 正: `title: "ヤーキズ＝ドッドソンの法則"`
- 誤: `title: "ヤーキズ＝ドッドソンの法則 Yerkes-Dodson Law"`

### F3. パーマリンク（slug）に日本語を入れない

フロントマターに英語（ローマ字）の `slug` を **必ず** 付ける。付けないと WordPress が日本語タイトルから日本語パーマリンクを自動生成してしまう。

- 例: `slug: "yerkes-dodson-law"`
- `scripts/post_to_wp.py` は `slug` があれば payload に載せて送る。

### F4. 最小限の説明 / excerpt

`## 最小限の説明` と `excerpt` は完全一致させる。20〜35文字・句点なし・名詞で締める（「〜という法則」「〜する傾向」「〜という現象」）。本文の体言止め禁止の例外として、ここだけは名詞で言い切ってよい。中身の書き方（定義の型・条件の核・用語名と同じ向き・限定語を落とさない）は 02_polishing.md の P2 と記事構成フォーマットに従う。

### F5. 提唱者の顔写真を毎回必ず入れる

毎回指示されなくても、投稿時に提唱者のポートレートを入れる。`## 語源・提唱者` の人物について Wikipedia の画像を取得し、**小さめ・中央寄せ**で、**キャプションに引用元URL** を付ける。肖像が存在しない人物（API が `NONE`）はスキップする。

画像URLは Wikipedia の pageimages API で取得する（サンドボックスで空が返るときは Desktop Commander でローカル実行）:

```
curl -s "https://en.wikipedia.org/w/api.php?action=query&titles={人物名}&prop=pageimages&piprop=original&format=json" | python3 -c "import sys,json; p=list(json.load(sys.stdin)['query']['pages'].values())[0]; print(p.get('original',{}).get('source','NONE'))"
```

挿入HTML（小さめ・中央・引用元URL入り）:

```html
<figure style="text-align:center;margin:1.5em auto;"><img src="{image_url}" alt="{name_katakana}" style="width:200px;max-width:45%;height:auto;display:block;margin:0 auto;"><figcaption style="font-size:0.85em;color:#666;">{name_katakana}（出典：{引用元URL}）</figcaption></figure>
```

### F6. 外部公開記事なので特定企業に寄せない（中立性）

UX TIMES は外部向けの一般記事である。本文・タイトル・`excerpt`（最小限の説明）・関連用語のどこにも、特定企業名（OPENLOGI 等）や、その企業固有の物流・EC 文脈への絞り込みを **入れない**。用語は中立的な一般解説として書く。

- ユーザー個人設定の「会社名は OPENLOGI 表記」ルールは社内文書向けであり、UX TIMES 記事には **適用しない**（例外として扱う）。
- 具体例を挙げるときも特定企業に寄せず、広く通用する例を選ぶ。

### 関門（生成と推敲の工程に組み込んだ機械的な確認）

文章のルールを足すより、工程で止める。次の3つは article-creator / article-review の手順に組み込んである。

- **出典台帳**：初稿と一緒に `research/{topic}_claims.md` を作り、本文の事実文をすべて台帳の引用と対にする。対にできない文は Doc 化の前に削る（P1）。
- **成立条件メモ**：`research/{topic}_conditions.md` に、成り立つ条件・隣の用語との境界・通し例を書く。リード文・各セクション・挿絵・実務の例を、すべてこの条件で確かめる（P2・P5）。
- **挿絵は確認済みの本文から作る**：挿絵の指示文は、事実確認を終えた本文の通し例から作る。本文を直したら、挿絵が条件を満たす例を描いているかを確かめ直す。
