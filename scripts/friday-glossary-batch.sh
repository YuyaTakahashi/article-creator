#!/bin/bash
# UX TIMES 用語集 金曜・生成リクエスト消化バッチ
# 実行タイミング: 毎週金曜 15:00（launchd: com.uxtimes.friday-glossary）
# Slackの生成リクエスト（用語DBの G列「生成する」=TRUE かつ H列=提案中）が「ある時だけ」走る。
# 0件なら claude を起動せず即終了する。1件以上あれば article-creator 無人で生成→Doc化→update_row→notifyで告知。
#
# 手動で今すぐ消化したいときは --quiet を付ける。生成・Doc化・用語DBの書き戻しは同じで、
# Slack告知だけ出さない（告知は月曜レポートがまとめて出す）。
#   bash scripts/friday-glossary-batch.sh --quiet
set -uo pipefail

NOTIFY_DIRECTIVE="Slack告知: する"
QUIET_LABEL=""
if [ "${1:-}" = "--quiet" ] || [ "${1:-}" = "-q" ]; then
  NOTIFY_DIRECTIVE="Slack告知: しない"
  QUIET_LABEL="（Slack告知なし）"
fi

BASE=/Users/takahashi_yuya/workspace/article-creator
SHEET=1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY
TODAY=$(date "+%Y-%m-%d")
mkdir -p "${BASE}/logs"
LOG="${BASE}/logs/friday-batch-${TODAY}.log"

cd "${BASE}" || exit 1

# 事前チェック: 新規生成リクエスト（提案中 かつ G列=TRUE）と作り直しリクエスト（U列=TRUE）の件数を数える。
# 0件なら claude を起動しない（金曜は無リクエスト時は沈黙）。
REQ=$(gws sheets +read --spreadsheet "${SHEET}" --range "'UX TIMES 用語DB'!A1:V1000" --format json 2>/dev/null | python3 -c '
import sys, json
try:
    rows = json.load(sys.stdin).get("values", [])
except Exception:
    print(0); sys.exit(0)
n = 0
for r in rows[1:]:
    g = str(r[6]).strip().upper() if len(r) > 6 else ""    # G列: 生成する（新規）
    h = str(r[7]).strip() if len(r) > 7 else ""            # H列: ステータス
    u = str(r[20]).strip().upper() if len(r) > 20 else ""  # U列: 作り直し
    if (g == "TRUE" and h == "提案中") or u == "TRUE":
        n += 1
print(n)
' 2>/dev/null)
REQ=${REQ:-0}

echo "[$(date)] 金曜バッチ判定: 生成リクエスト ${REQ} 件" >> "${LOG}"
if [ "${REQ}" -eq 0 ] 2>/dev/null; then
  echo "[$(date)] リクエスト0件のためスキップ" >> "${LOG}"
  exit 0
fi

echo "[$(date)] 金曜バッチ開始（リクエスト ${REQ} 件）${QUIET_LABEL}" >> "${LOG}"

# 現行レシピ版を用語くん(GAS)に知らせる。版が上がっていれば用語くんがチャンネルに一報を入れる。
bash "${BASE}/scripts/sync_recipe_version.sh" "${LOG}"

# 無人実行のため権限プロンプトを出さない。出力は失敗判定のため一旦キャプチャする。
OUT=$(claude -p "$(cat "${BASE}/pipeline/friday-request-batch-prompt.md")

${NOTIFY_DIRECTIVE}" --dangerously-skip-permissions 2>&1)
printf '%s\n' "${OUT}" >> "${LOG}"

# claude が起動/認証できない・一時エラー・空出力 → Slackを出さず静かに終了。
# 生成リクエスト（G列=TRUE）は消化されず残るので、次の週次バッチ（2時間おき）がリトライで拾う。
if [ -z "${OUT}" ] || printf '%s' "${OUT}" | grep -qiE "Not logged in|Please run /login|Invalid API key|Credit balance|Connection closed|API Error"; then
  echo "[$(date)] claude起動不可/一時エラー/空出力 → Slackを出さず終了（リクエストは残置、週次バッチがリトライ）" >> "${LOG}"
  exit 0
fi

echo "[$(date)] 金曜バッチ終了  ログ: ${LOG}" >> "${LOG}"
