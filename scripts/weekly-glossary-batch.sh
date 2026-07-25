#!/bin/bash
# UX TIMES 用語集 週次ドラフト生成バッチ
# 実行タイミング: 毎週月曜 10:00（launchd: com.uxtimes.weekly-glossary）
# 提案中の用語から3本（Slack追加分優先→登場回数順）を article-creator 無人で生成し、
# Doc化 → update_row 書き戻し → notify でSlackダイジェスト投稿する。
set -uo pipefail

BASE=/Users/takahashi_yuya/workspace/article-creator
TODAY=$(date "+%Y-%m-%d")
mkdir -p "${BASE}/logs"
LOG="${BASE}/logs/weekly-batch-${TODAY}.log"

cd "${BASE}" || exit 1
echo "[$(date)] 週次バッチ開始" >> "${LOG}"

# 無人実行のため権限プロンプトを出さない（article-creator は多様なツールを使うため allow を絞らない）。
claude -p "$(cat "${BASE}/pipeline/weekly-batch-prompt.md")" \
  --dangerously-skip-permissions >> "${LOG}" 2>&1

echo "[$(date)] 週次バッチ終了 (exit $?)" >> "${LOG}"
