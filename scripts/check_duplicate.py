#!/usr/bin/env python3
"""
WordPress(uxdaystokyo.com)に同名・類似の用語記事が既に無いかを確認するローカル実行スクリプト。

Coworkサンドボックスからは外部HTTPSがブロックされるため、ディープリサーチ/執筆に入る前の
重複チェックは、このスクリプトをローカル（Mac）で実行して行う。

使い方:
    cd ~/workspace/article-creator
    python3 scripts/check_duplicate.py "コンテキストアウェアネス"
    python3 scripts/check_duplicate.py "Context Awareness" "コンテキストアウェアネス"   # 複数語でOR検索

判定の考え方:
    WP REST の search は本文の全文を対象にするため、無関係な記事の本文に語が出てくる
    だけでヒットする（例: CAGR で「チャンキング」が返る）。これをそのまま重複扱いにすると、
    ハードゲートが誤って生成を止めてしまう。
    そこで検索結果を2つに分ける。
      - タイトル・slug が一致する    → 本物の重複候補。生成を止める（exit 2）
      - 本文に語が出てくるだけ        → 参考として表示するだけ。生成は止めない（exit 0）

終了コード:
    0 = 重複なし（先に進んでよい）
    2 = 重複候補あり（新規作成を止めて人間に確認）
"""

import html
import re
import sys
import json
import base64
import unicodedata
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


def norm(s: str) -> str:
    """全角半角・記号・空白の揺れを吸収して比較できる形にする。"""
    s = html.unescape(str(s))
    s = re.sub(r"<[^>]+>", "", s)
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"[\s　・･/／\-—–_（）()\[\]「」『』,、。.]", "", s)


def slugify(s: str) -> str:
    """英字の用語を slug 形式に寄せる（CAGR → cagr）。日本語だけなら空文字。"""
    s = unicodedata.normalize("NFKC", str(s)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def title_or_slug_match(post, terms) -> bool:
    """タイトルか slug が用語と一致するときだけ「本物の重複候補」とみなす。"""
    ntitle = norm(post.get("title", {}).get("rendered", ""))
    pslug = str(post.get("slug", "") or "").strip("-")
    for term in terms:
        nt = norm(term)
        if not nt:
            continue
        # 2文字以下の語は部分一致だと当たりすぎるので完全一致だけ見る
        if nt == ntitle:
            return True
        if len(nt) >= 3 and ntitle and (nt in ntitle or ntitle in nt):
            return True
        ts = slugify(term)
        if ts and pslug:
            if ts == pslug:
                return True
            # cagr と cagr-2（WPが重複時に付ける連番）を同じものとして扱う
            if re.fullmatch(re.escape(ts) + r"(-\d+)?", pslug):
                return True
    return False


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


def search_by_slug(env, slug):
    """slug 完全一致で引く。search では取りこぼすことがあるため併用する。"""
    site = env["WP_SITE_URL"].rstrip("/")
    auth = base64.b64encode(
        f'{env["WP_USER"]}:{env["WP_APP_PASS"].replace(" ", "")}'.encode()).decode()
    post_type = env.get("WP_POST_TYPE", "posts")
    q = urllib.parse.urlencode({"slug": slug, "status": "publish,draft,future,pending"})
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

    # slug でも直接引く。search は本文寄りの挙動なので、slug 完全一致を取りこぼすことがある。
    for term in terms:
        ts = slugify(term)
        if not ts:
            continue
        try:
            for p in search_by_slug(env, ts):
                seen[p["id"]] = p
        except urllib.error.HTTPError:
            pass

    hits = sorted(seen.values(), key=lambda x: x["id"])
    strong = [p for p in hits if title_or_slug_match(p, terms)]
    weak = [p for p in hits if p not in strong]

    def show(p):
        title = p.get("title", {}).get("rendered", "?")
        print(f"  - id={p['id']} status={p.get('status')} slug={p.get('slug')}")
        print(f"    title: {title}")
        print(f"    link : {p.get('link')}")

    if not strong:
        print(f"重複なし: {terms} と同じタイトル・slug の既存記事は見つかりませんでした。新規作成して問題ありません。")
        if weak:
            print(f"（参考: 本文に語が出てくるだけの記事が {len(weak)}件ありました。重複ではないので止めません）")
            for p in weak:
                show(p)
        sys.exit(0)

    print(f"⚠ 重複候補あり（{len(strong)}件）: 新規作成の前に確認してください。")
    for p in strong:
        show(p)
    if weak:
        print(f"（参考: 本文に語が出てくるだけの記事が {len(weak)}件。判定には使っていません）")
    sys.exit(2)


if __name__ == "__main__":
    main()
