#!/usr/bin/env python3
"""
related-term-candidates.json の候補を、GAS Webhook(add_term)経由で
「UX TIMES 用語DB」シートに一括追記するローカル実行スクリプト。

前提: gas-webhook.gs をシートにデプロイし、.env に次を追記しておく:
    GAS_WEBAPP_URL=https://script.google.com/macros/s/xxxx/exec
    GAS_TOKEN=<gas-webhook.gs の SECRET_TOKEN と同じ文字列>

使い方:
    cd ~/workspace/article-creator
    python3 scripts/push_candidates_to_sheet.py --dry-run   # 送信内容だけ確認
    python3 scripts/push_candidates_to_sheet.py             # 実際に追記(silent)

Coworkサンドボックスからは外部HTTPSが403になるため、必ずローカル(Mac)で実行する。
add_term はシート側でIDを採番するので、TSVのG-005…とは別に一意IDが振られる。
"""

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_env(env_path: Path) -> dict:
    env = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        env[k.strip()] = v.split(" #")[0].strip()
    return env


def post(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    dry = "--dry-run" in sys.argv
    env = load_env(REPO / ".env")
    url = env.get("GAS_WEBAPP_URL", "")
    token = env.get("GAS_TOKEN", "")
    if not dry and (not url or not token):
        sys.stderr.write(
            "GAS_WEBAPP_URL / GAS_TOKEN が .env にありません。\n"
            "gas-webhook.gs をデプロイして .env に追記してから再実行してください。\n"
            "（送信内容だけ見るなら --dry-run を付けてください）\n")
        sys.exit(1)

    data = json.loads((REPO / "pipeline" / "related-term-candidates.json").read_text(encoding="utf-8"))
    cands = [c for c in data["candidates"] if not c.get("in_sheet_already")]
    print(f"追記対象: {len(cands)}件  (dry_run={dry})")

    ok = ng = 0
    for i, c in enumerate(cands, 1):
        note = f"公開記事{c['count']}本の関連用語に登場（例: {c['sources'][0] if c['sources'] else ''}）"
        payload = {
            "token": token, "action": "add_term", "silent": True,
            "term": c["term"], "term_en": c.get("english", ""),
            "context": "関連用語ギャップから自動抽出", "proposer": "関連用語抽出",
            "note": note,
        }
        if dry:
            print(f"  [{i:>2}] {c['term']}  (en={c.get('english','')})")
            continue
        try:
            r = post(url, payload)
            if r.get("ok"):
                ok += 1
                print(f"  [{i:>2}] OK {r.get('id')}  {c['term']}")
            else:
                ng += 1
                print(f"  [{i:>2}] NG {c['term']}: {r.get('error')}")
        except urllib.error.URLError as e:
            ng += 1
            print(f"  [{i:>2}] NG {c['term']}: {e}")
        time.sleep(0.3)  # GAS実行の連打を避ける

    if not dry:
        print(f"\n完了: 成功 {ok}件 / 失敗 {ng}件")


if __name__ == "__main__":
    main()
