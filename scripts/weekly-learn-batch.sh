#!/bin/bash
# UX TIMES 用語集 週次・編集差分の学習バッチ
# 実行タイミング: launchd（com.uxtimes.weekly-learn）が週1回起動する想定。
# 公開された記事の「AI初稿 → 人が直した公開版」の差分を集め、執筆ルールの改訂材料として積む。
# プロンプトは書き換えない。反映は人が決める。Slackにも投稿しない。
#
# 手動で回すとき: bash scripts/weekly-learn-batch.sh
set -uo pipefail

BASE=/Users/takahashi_yuya/workspace/article-creator
TODAY=$(date "+%Y-%m-%d")
WEEK=$(date "+%G-W%V")
mkdir -p "${BASE}/logs"
LOG="${BASE}/logs/learn-batch-${TODAY}.log"
MARKER="${BASE}/logs/learn-done-${WEEK}.marker"

cd "${BASE}" || exit 1

# 今週すでに成功していれば何もしない（定期リトライの冪等ガード）
if [ -f "${MARKER}" ]; then
  exit 0
fi

# 事前チェック: 差分を取る対象（公開済み・wp_post_idあり・W列が空）が無ければ claude を起動しない
PENDING=$(python3 scripts/collect_edit_gaps.py --dry-run --out-dir "$(mktemp -d)" 2>/dev/null | grep -c "^  G-" || true)
PENDING=${PENDING:-0}
echo "[$(date)] 学習バッチ判定: 未確認の公開記事 ${PENDING} 件" >> "${LOG}"
if [ "${PENDING}" -eq 0 ] 2>/dev/null; then
  echo "[$(date)] 対象0件のためスキップ（完了マークはしない）" >> "${LOG}"
  exit 0
fi

echo "[$(date)] 学習バッチ開始（${PENDING} 件）" >> "${LOG}"

OUT=$(claude -p "$(cat "${BASE}/pipeline/learn-from-edits-prompt.md")" --dangerously-skip-permissions 2>&1)
printf '%s\n' "${OUT}" >> "${LOG}"

# claude が起動/認証できない・一時エラー・空出力 → 完了マークせず終了（次回リトライ）
if [ -z "${OUT}" ] || printf '%s' "${OUT}" | grep -qiE "Not logged in|Please run /login|Invalid API key|Credit balance|Connection closed|API Error"; then
  echo "[$(date)] claude起動不可/一時エラー/空出力 → 完了マークせず終了（次回リトライ）" >> "${LOG}"
  exit 0
fi

touch "${MARKER}"
echo "[$(date)] 学習バッチ成功・完了マーク作成: ${MARKER}" >> "${LOG}"
