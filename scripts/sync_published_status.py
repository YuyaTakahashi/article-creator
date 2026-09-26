#!/usr/bin/env python3
"""WPで公開された記事を、用語DBのステータスにも「公開済み」として反映する。

WPで公開ボタンを押しても用語DBは書き換わらない。放っておくと公開済みの記事が
「レビュー待ち」のまま残り、collect_edit_gaps.py（公開済みだけを見る）が差分を取らない。
wp_post_id がある行についてWPの status を見て、publish なら H列を「公開済み」にする。

触らない行:
  - 公開済み        … すでに合っている
  - 作り直し済み    … 公開中の記事を書き直した版。WPは旧版のまま publish なので、ここで戻すと取り違える
  - 見送り          … 人が止めた行

使い方:
    python3 scripts/sync_published_status.py            # 反映する
    python3 scripts/sync_published_status.py --dry-run  # 変わる行を表示するだけ
"""

import argparse
import base64
import json
import subprocess
import sys
import urllib.error
import urllib.request

from collect_edit_gaps import SHEET_ID, TAB, load_env, read_sheet

PUBLISHED = "公開済み"
SKIP = {PUBLISHED, "作り直し済み", "見送り"}
STATUS_COL = "H"


def wp_status(env, post_id):
    site = env["WP_SITE_URL"].rstrip("/")
    post_type = env.get("WP_POST_TYPE", "posts")
    auth = base64.b64encode(
        f"{env['WP_USER']}:{env['WP_APP_PASS'].replace(' ', '')}".encode()).decode()
    # context=edit にしないと下書き・非公開は 401/404 になり、status が読めない
    req = urllib.request.Request(
        f"{site}/wp-json/wp/v2/{post_type}/{post_id}?context=edit&_fields=status",
        headers={"Authorization": "Basic " + auth})
    return json.loads(urllib.request.urlopen(req, timeout=30).read()).get("status", "")


def set_status(row_no, value):
    out = subprocess.run(
        ["gws", "sheets", "spreadsheets", "values", "update",
         "--params", json.dumps({"spreadsheetId": SHEET_ID,
                                 "range": f"{TAB}!{STATUS_COL}{row_no}",
                                 "valueInputOption": "USER_ENTERED"}),
         "--json", json.dumps({"values": [[value]]})],
        capture_output=True, text=True)
    return '"updatedCells": 1' in out.stdout


def main():
    ap = argparse.ArgumentParser(description="WPの公開状態を用語DBのステータスに反映する")
    ap.add_argument("--dry-run", action="store_true", help="用語DBを書き換えない")
    args = ap.parse_args()

    env = load_env()
    rows = read_sheet()

    def g(r, k):
        return str(r[k]).strip() if len(r) > k else ""

    changed = failed = 0
    for row_no, r in enumerate(rows[1:], start=2):
        gid, term, status, wp_id = g(r, 0), g(r, 1), g(r, 7), g(r, 16)
        if not wp_id or status in SKIP:
            continue
        try:
            st = wp_status(env, wp_id)
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            print(f"  {gid} {term}: WPを読めなかった（{e}）→ 飛ばす")
            failed += 1
            continue
        if st != "publish":
            continue
        if args.dry_run:
            print(f"  {gid} {term}: {status} → {PUBLISHED}（dry-run）")
            changed += 1
        elif set_status(row_no, PUBLISHED):
            print(f"  {gid} {term}: {status} → {PUBLISHED}")
            changed += 1
        else:
            print(f"  {gid} {term}: 用語DBの更新に失敗")
            failed += 1

    print(f"公開状態の同期: 更新 {changed} 件 / 失敗 {failed} 件")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
