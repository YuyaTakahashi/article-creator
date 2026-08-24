# article-creator レシピ変更履歴

記事の書きぶりを決めるプロンプト群（prompts/recipe-manifest.txt）の変更履歴。
各記事のフロントマター `creator_version` はここの版番号を指す。

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

