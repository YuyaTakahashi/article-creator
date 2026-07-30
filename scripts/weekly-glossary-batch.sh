#!/bin/bash
# UX TIMES 用語集 週次ドラフト生成バッチ（定期リトライ対応）
# 実行タイミング: launchd（com.uxtimes.weekly-glossary）が2時間おきに起動する。
# 週ごとの完了マーカーで冪等化し、その週にまだ成功していなければ生成を試みる。
# claude が起動/認証できない（Not logged in 等）・一時エラー・空出力のときは、
# Slackを出さず・完了マークもせず静かに終了し、次回の起動でリトライする。
set -uo pipefail

BASE=/Users/takahashi_yuya/workspace/article-creator
TODAY=$(date "+%Y-%m-%d")
WEEK=$(date "+%G-W%V")          # ISO年-週（週の単位で完了管理）
mkdir -p "${BASE}/logs"
LOG="${BASE}/logs/weekly-batch-${TODAY}.log"
MARKER="${BASE}/logs/weekly-done-${WEEK}.marker"

cd "${BASE}" || exit 1

# 今週すでに生成成功済みなら何もしない（定期リトライの冪等ガード＝重複生成の防止）
if [ -f "${MARKER}" ]; then
  exit 0
fi

echo "[$(date)] 週次バッチ開始（week ${WEEK}）" >> "${LOG}"

# 無人実行のため権限プロンプトを出さない。出力は失敗判定のため一旦キャプチャする。
OUT=$(claude -p "$(cat "${BASE}/pipeline/weekly-batch-prompt.md")" --dangerously-skip-permissions 2>&1)
printf '%s\n' "${OUT}" >> "${LOG}"

# claude が起動/認証できない・一時エラー・空出力 → Slackも完了マークも出さず静かに終了（次回リトライ）
if [ -z "${OUT}" ] || printf '%s' "${OUT}" | grep -qiE "Not logged in|Please run /login|Invalid API key|Credit balance|Connection closed|API Error"; then
  echo "[$(date)] claude起動不可/一時エラー/空出力 → 完了マークせず終了（次回リトライ）" >> "${LOG}"
  exit 0
fi

# 成功: 今週分の完了マークを付ける（以降このweekは再生成しない）
touch "${MARKER}"
echo "[$(date)] 週次バッチ成功・完了マーク作成: ${MARKER}" >> "${LOG}"
