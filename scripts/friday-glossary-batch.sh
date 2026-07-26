#!/bin/bash
# UX TIMES 用語集 金曜・生成リクエスト消化バッチ
# 実行タイミング: 毎週金曜 15:00（launchd: com.uxtimes.friday-glossary）
# Slackの生成リクエスト（用語DBの G列「生成する」=TRUE かつ H列=提案中）が「ある時だけ」走る。
# 0件なら claude を起動せず即終了する。1件以上あれば article-creator 無人で生成→Doc化→update_row→notifyで告知。
set -uo pipefail

BASE=/Users/takahashi_yuya/workspace/article-creator
SHEET=1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY
TODAY=$(date "+%Y-%m-%d")
mkdir -p "${BASE}/logs"
LOG="${BASE}/logs/friday-batch-${TODAY}.log"

cd "${BASE}" || exit 1

# 事前チェック: 提案中(H列=8) かつ 生成する(G列=7)=TRUE のリクエスト件数を数える。
# 0件なら claude を起動しない（金曜は無リクエスト時は沈黙）。
REQ=$(gws sheets +read --spreadsheet "${SHEET}" --range "'UX TIMES 用語DB'!A1:R80" --format json 2>/dev/null | python3 -c '
import sys, json
try:
    rows = json.load(sys.stdin).get("values", [])
except Exception:
    print(0); sys.exit(0)
n = 0
for r in rows[1:]:
    g = str(r[6]).strip().upper() if len(r) > 6 else ""   # G列: 生成する
    h = str(r[7]).strip() if len(r) > 7 else ""            # H列: ステータス
    if g == "TRUE" and h == "提案中":
        n += 1
print(n)
' 2>/dev/null)
REQ=${REQ:-0}

echo "[$(date)] 金曜バッチ判定: 生成リクエスト ${REQ} 件" >> "${LOG}"
if [ "${REQ}" -eq 0 ] 2>/dev/null; then
  echo "[$(date)] リクエスト0件のためスキップ" >> "${LOG}"
  exit 0
fi

echo "[$(date)] 金曜バッチ開始（リクエスト ${REQ} 件）" >> "${LOG}"

# 無人実行のため権限プロンプトを出さない（article-creator は多様なツールを使うため allow を絞らない）。
claude -p "$(cat "${BASE}/pipeline/friday-request-batch-prompt.md")" \
  --dangerously-skip-permissions >> "${LOG}" 2>&1

echo "[$(date)] 金曜バッチ終了 (exit $?)  ログ: ${LOG}" >> "${LOG}"
