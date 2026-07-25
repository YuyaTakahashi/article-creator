#!/bin/bash
# 月次トレンド用語探索（毎月「第1金曜日」のみ実行）
# launchd（com.uxtimes.monthly-trend）から毎週金曜17時に呼ばれ、第1金曜以外は何もせず終了する。
# WebSearchでトレンド用語を探し、用語DBに add_term → チャンネルに notify で告知する。
set -uo pipefail

BASE=/Users/takahashi_yuya/workspace/article-creator

# 第1金曜日のみ実行（その月で日付が1〜7の金曜）。10# は先頭ゼロ(08,09)の8進数誤解釈を防ぐ。
DAY=$(date +%d)
if [ "$((10#$DAY))" -gt 7 ]; then
  exit 0
fi

TODAY=$(date "+%Y-%m-%d")
mkdir -p "${BASE}/logs"
LOG="${BASE}/logs/monthly-trend-${TODAY}.log"

cd "${BASE}" || exit 1
echo "[$(date)] 月次トレンド開始（第1金曜）" >> "${LOG}"

claude -p "$(cat "${BASE}/pipeline/monthly-trend-prompt.md")" \
  --dangerously-skip-permissions >> "${LOG}" 2>&1

echo "[$(date)] 月次トレンド終了 (exit $?)  ログ: ${LOG}" >> "${LOG}"
