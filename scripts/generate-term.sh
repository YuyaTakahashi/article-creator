#!/bin/bash
# 指定した用語1件を article-creator でドラフト化する（オンデマンド）
# 使い方: bash scripts/generate-term.sh "人工的希少性"
#   用語DBに無ければ自動で追加してから生成する。Doc化→用語DB書き戻しまで行う（Slack投稿はしない）。
set -uo pipefail

BASE=/Users/takahashi_yuya/workspace/article-creator
TERM="${1:-}"
if [ -z "$TERM" ]; then
  echo "使い方: bash scripts/generate-term.sh \"用語名\""
  exit 1
fi

TODAY=$(date "+%Y-%m-%d")
mkdir -p "${BASE}/logs"
LOG="${BASE}/logs/generate-term-${TODAY}.log"

cd "${BASE}" || exit 1
echo "[$(date)] 単発生成: ${TERM}" >> "${LOG}"

claude -p "$(cat "${BASE}/pipeline/generate-term-prompt.md")

対象用語: ${TERM}" \
  --dangerously-skip-permissions >> "${LOG}" 2>&1

echo "[$(date)] 単発生成 終了 (exit $?)  ログ: ${LOG}" >> "${LOG}"
echo "完了。ログ: ${LOG}"
