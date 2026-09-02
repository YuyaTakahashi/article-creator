# article-creator レシピ変更履歴

記事の書きぶりを決めるプロンプト群（prompts/recipe-manifest.txt）の変更履歴。
各記事のフロントマター `creator_version` はここの版番号を指す。

## v8 — 2026-09-02

統計値の密度を難易度に依らず抑制し、既存概念の改良・発展形はベース概念との対比を導入部に含める。見出しの主語省略は一意に推測できる場合に限定。reader-criticの数値評価とtemplate-criticのタイトル形式ルールを実際の生成ルール（日本語のみ）に整合させた

レシピhash: `e2f29ce6fc95`

変更されたファイル:
  - .agent/skills/article-critic/references/reader-critic.md
  - .agent/skills/article-critic/references/template-critic.md
  - prompts/01_information_gathering.md
  - prompts/02_polishing.md

## v7 — 2026-09-01

語源・提唱者のあとに続く内容セクションを効果/実務でどう使われるかの2つに絞るルールを追加(仕組み・原理は定義セクションへ、対比・反論は効果セクションへ統合)。CLAUDE.md/01_information_gathering.md/02_polishing.mdとarticle-criticのtemplate-critic.mdのH2構成順序ルーブリックに反映

レシピhash: `525ad6c873d4`

変更されたファイル:
  - .agent/skills/article-critic/references/template-critic.md
  - CLAUDE.md
  - prompts/01_information_gathering.md
  - prompts/02_polishing.md

## v6 — 2026-09-01

提唱の根拠になった実験(心理学実験など)がある場合、実験の内容(仮説・対象・方法・結果)を提唱者の経歴・動機を語る段落と混ぜず独立した段落/セクションとして書くルールを追加。CLAUDE.md/01_information_gathering.md/02_polishing.mdと、article-criticのtemplate-critic.mdの評価基準に反映

レシピhash: `9cf6c322f97f`

変更されたファイル:
  - .agent/skills/article-critic/references/template-critic.md
  - CLAUDE.md
  - prompts/01_information_gathering.md
  - prompts/02_polishing.md

## v5 — 2026-09-01

article-criticスキルを新規追加。Step5.5/8.5の品質ゲートが自己採点の代用ではなく実体のスキルとして動くようになる（テンプレ準拠/文章スタイル/読み手目線/読みやすさの4軸ルーブリック）

レシピhash: `d93b0cce0791`

変更されたファイル:
  - .agent/skills/article-critic/SKILL.md（レシピに追加）
  - .agent/skills/article-critic/references/readability-critic.md（レシピに追加）
  - .agent/skills/article-critic/references/reader-critic.md（レシピに追加）
  - .agent/skills/article-critic/references/style-critic.md（レシピに追加）
  - .agent/skills/article-critic/references/template-critic.md（レシピに追加）

## v4 — 2026-09-01

実務セクションの4点を重要度順にし、裏づけのない項目は落としてよい形に緩和。article-critic を Step 5.5 / 8.5 の必須ゲートとして SKILL に復帰。reviewed_at は scripts/mark_reviewed.py だけが刻む形に変更。

レシピhash: `89d40f87026e`

変更されたファイル:
  - .agent/skills/article-creator/SKILL.md
  - .agent/skills/article-review/SKILL.md
  - CLAUDE.md
  - prompts/01_information_gathering.md
  - prompts/02_polishing.md

## v3 — 2026-08-24

編集差分からの学習を反映（CAGRへのフィードバック）。①1段落に結論をひとつだけ置き、似た締めの文を連ねない ②語源・提唱者では普及した事実だけでなく、なぜ普及したのかの理由を添える。

レシピhash: `bd2516dfe937`

変更されたファイル:
  - prompts/02_polishing.md

## v2 — 2026-08-24

編集差分からの学習を反映。①セクションをまたいだ内容の繰り返しを止める（実務の具体例は定義と別のタスク種類にする／セクション冒頭の結論文を次文の言い換えにしない）②改名された用語は現行語を優先し、関連用語は日本語のみで本文既出語を重ねない。

レシピhash: `1d507a396a52`

変更されたファイル:
  - prompts/02_polishing.md

## v1 — 2026-08-22

- 2026-08-24 版を据え置いたまま lock を更新（刻印手順に --backfill を使わない注意を追記。執筆の指示は変えていない） — 対象: .agent/skills/article-creator/SKILL.md

- 2026-08-24 版を据え置いたまま lock を更新（スキル説明とStep 10の導入文を更新。執筆の指示は変えていない） — 対象: .agent/skills/article-creator/SKILL.md

- 2026-08-24 版を据え置いたまま lock を更新（Step 10（Doc化と用語DB反映）を追加。執筆の指示は変えていない） — 対象: .agent/skills/article-creator/SKILL.md

- 2026-08-24 版を据え置いたまま lock を更新（Coworkでも刻印コマンドが通るよう REPO_BASH フォールバックを追加（本文の書きぶりは変えていない）） — 対象: .agent/skills/article-creator/SKILL.md

初版。バージョン管理を始めた時点のレシピ（背景・目的／効果の前後対比／実務での使い方を必須化 まで反映済み）。生成時に scripts/stamp_version.py で版を刻む運用をここから開始する。

レシピhash: `cf04c3f72083`

変更されたファイル:
  - .agent/skills/article-creator/SKILL.md（レシピに追加）
  - .agent/skills/article-review/SKILL.md（レシピに追加）
  - CLAUDE.md（レシピに追加）
  - prompts/01_information_gathering.md（レシピに追加）
  - prompts/02_polishing.md（レシピに追加）
  - prompts/03_eyecatch.md（レシピに追加）

