# article-creator レシピ変更履歴

記事の書きぶりを決めるプロンプト群（prompts/recipe-manifest.txt）の変更履歴。
各記事のフロントマター `creator_version` はここの版番号を指す。

## v1 — 2026-08-22

初版。バージョン管理を始めた時点のレシピ（背景・目的／効果の前後対比／実務での使い方を必須化 まで反映済み）。生成時に scripts/stamp_version.py で版を刻む運用をここから開始する。

レシピhash: `cf04c3f72083`

変更されたファイル:
  - .agent/skills/article-creator/SKILL.md（レシピに追加）
  - .agent/skills/article-review/SKILL.md（レシピに追加）
  - CLAUDE.md（レシピに追加）
  - prompts/01_information_gathering.md（レシピに追加）
  - prompts/02_polishing.md（レシピに追加）
  - prompts/03_eyecatch.md（レシピに追加）

