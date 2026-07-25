#!/usr/bin/env python3
"""
WordPress(uxdaystokyo.com)に同名・類似の用語記事が既に無いかを確認するローカル実行スクリプト。

Coworkサンドボックスからは外部HTTPSがブロックされるため、ディープリサーチ/執筆に入る前の
重複チェックは、このスクリプトをローカル（Mac）で実行して行う。

使い方:
    cd ~/workspace/article-creator
    python3 scripts/check_duplicate.py "コンテキストアウェアネス"
    python3 scripts/check_duplicate.py "Context Awareness" "コンテキストアウェアネス"   # 複数語でOR検索

終了コード:
    0 = 重複なし（先に進んでよい）
    2 = 重複候補あり（新規作成を止めて人間に確認）
"""

import sys
import json
import base64
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path


def load_env(env_path: Path) -> dict:
    env = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        env[k.strip()] = v
    return env


def search(env, term):
    site = env["WP_SITE_URL"].rstrip("/")
    user = env["WP_USER"]
    app_pass = env["WP_APP_PASS"].replace(" ", "")
    post_type = env.get("WP_POST_TYPE", "posts")
    auth = base64.b64encode(f"{user}:{app_pass}".encode()).decode()

    q = urllib.parse.urlencode({
        "search": term,
        "per_page": 10,
        "status": "publish,draft,future,pending",
    })
    url = f"{site}/wp-json/wp/v2/{post_type}?{q}"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    if len(sys.argv) < 2:
        sys.stderr.write('usage: python3 scripts/check_duplicate.py "用語" ["別表記" ...]\n')
        sys.exit(1)

    repo_root = Path(__file__).resolve().parents[1]
    env = load_env(repo_root / ".env")

    terms = sys.argv[1:]
    seen = {}
    for term in terms:
        try:
            for p in search(env, term):
                seen[p["id"]] = p
        except urllib.error.HTTPError as e:
            sys.stderr.write(f"HTTP {e.code}: {e.read().decode(errors='replace')}\n")
            sys.exit(1)

    if not seen:
        print(f"重複なし: {terms} に一致する既存記事は見つかりませんでした。新規作成して問題ありません。")
        sys.exit(0)

    print(f"⚠ 重複候補あり（{len(seen)}件）: 新規作成の前に確認してください。")
    for p in sorted(seen.values(), key=lambda x: x["id"]):
        title = p.get("title", {}).get("rendered", "?")
        print(f"  - id={p['id']} status={p.get('status')} slug={p.get('slug')}")
        print(f"    title: {title}")
        print(f"    link : {p.get('link')}")
    sys.exit(2)


if __name__ == "__main__":
    main()
