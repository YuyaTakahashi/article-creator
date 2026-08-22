#!/bin/bash
# 現行のレシピ版（article-creator のプロンプト群のバージョン）を用語くん(GAS)に知らせる。
# 用語くんはこれを受けて「この記事は旧版だ」「作り直しリクエストを受けるか」を判断する。
#
# 生成バッチの先頭で呼ぶ。版が上がっていれば用語くんがチャンネルに一報を入れる。
# 使い方: bash scripts/sync_recipe_version.sh [ログファイル]
set -uo pipefail

BASE=/Users/takahashi_yuya/workspace/article-creator
LOG="${1:-/dev/null}"
cd "${BASE}" || exit 0

# レシピを直したのに版を上げていない（+dirty）ときは記録に残す。バッチは止めない。
if ! python3 scripts/recipe_version.py check >>"${LOG}" 2>&1; then
  echo "[$(date)] 警告: レシピ版が未確定(+dirty)のまま生成する。bump しておくこと" >> "${LOG}"
fi

STATE=$(python3 scripts/recipe_version.py current --json 2>/dev/null)
[ -z "${STATE}" ] && exit 0

VERSION=$(printf '%s' "${STATE}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["version"])' 2>/dev/null)
HASH=$(printf '%s' "${STATE}" | python3 -c 'import sys,json; print(json.load(sys.stdin)["hash"])' 2>/dev/null)
[ -z "${VERSION}" ] && exit 0

# .env から webhook 設定を読む（値はログに出さない）
set -a; . "${BASE}/.env" 2>/dev/null; set +a
if [ -z "${GAS_WEBAPP_URL:-}" ] || [ -z "${GAS_TOKEN:-}" ]; then
  echo "[$(date)] GAS webhook 未設定のためレシピ版の通知をスキップ（${VERSION}）" >> "${LOG}"
  exit 0
fi

NOTE=$(python3 - <<'PY' 2>/dev/null
import pathlib, re
p = pathlib.Path('prompts/CHANGELOG.md')
if p.exists():
    m = re.search(r'^## \S+ — \S+\n\n(.+)$', p.read_text(encoding='utf-8'), re.M)
    print(m.group(1).strip() if m else '')
PY
)

RESP=$(python3 - "${VERSION}" "${HASH}" "${NOTE}" <<'PY' 2>&1
import json, os, sys, urllib.request
version, hash_, note = sys.argv[1], sys.argv[2], sys.argv[3]
payload = json.dumps({
    "token": os.environ["GAS_TOKEN"], "action": "set_recipe_version",
    "version": version, "hash": hash_, "note": note, "announce": True,
}).encode("utf-8")
req = urllib.request.Request(os.environ["GAS_WEBAPP_URL"], data=payload,
                             headers={"Content-Type": "application/json"})
try:
    print(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
except Exception as e:
    print(f'{{"ok":false,"error":"{e}"}}')
PY
)
echo "[$(date)] レシピ版を用語くんに通知: ${VERSION} → ${RESP}" >> "${LOG}"
