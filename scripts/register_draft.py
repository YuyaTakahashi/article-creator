#!/usr/bin/env python3
"""生成済みの記事MDを用語DBに反映する（Doc化のあとの最後の一手）。

article-creator は drafts/*.md を作るところまでで終わる。そこから先の
「用語DBのどの行か探して、ステータス・Docリンク・メタデータ・レシピ版を書き戻す」を
このスクリプトが引き受ける。フロントマターを読むので、値を手で写す必要はない。

Cowork のサンドボックスからは GAS の webhook に届かない（外部HTTPSが403）。
Cowork で使うときは Desktop Commander 経由でこのスクリプトを実行する。
Doc化そのものは Drive コネクタ（create_file）が担当し、ここでは受け取った URL を書き戻すだけ。

使い方:
    python3 scripts/register_draft.py drafts/モーダル.md --doc-url "https://docs.google.com/..."
    python3 scripts/register_draft.py drafts/OOUX.md --doc-url "..." \
        --regenerated-from v0 --old-doc-url "https://docs.google.com/...旧..."
    python3 scripts/register_draft.py drafts/モーダル.md --doc-url "..." --dry-run

用語DBの行は、ファイル名（drafts/{用語}.md）を用語名として B列 から探す。
見つからなければ add_term で新しい行を作ってから書き戻す。--term で明示もできる。
"""

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SHEET_ID = "1GEhserUiXQIHG8xNl2jUdLvrD2fHzeWXGkdJ_sZGCgY"
TAB = "UX TIMES 用語DB"
# 行数は固定せず広めに読む。上限を切ると、超えた行の用語が「無い」と判定されて重複行が生える。
READ_RANGE = f"'{TAB}'!A1:V1000"
PUBLISHED = "公開済み"


def load_env():
    env = {}
    p = BASE / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("GAS_WEBAPP_URL", "GAS_TOKEN"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        sys.exit(f"フロントマターが無い: {path}")
    lines = text.split("\n")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        sys.exit(f"フロントマターが閉じていない: {path}")
    fm = {}
    for line in lines[1:end]:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return fm


def read_sheet():
    out = subprocess.run(
        ["gws", "sheets", "+read", "--spreadsheet", SHEET_ID, "--range", READ_RANGE, "--format", "json"],
        capture_output=True, text=True)
    body = out.stdout[out.stdout.find("{"):] if "{" in out.stdout else ""
    if not body:
        sys.exit(f"用語DBを読めなかった: {out.stderr.strip()[:200]}")
    return json.loads(body).get("values", [])


def norm(s):
    s = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"[\s　・（）()/]", "", s).lower()


def find_row(rows, term):
    """B列から用語を探す。表記ゆれ（全角半角・中黒・カッコ）は吸収する。"""
    for i, r in enumerate(rows[1:], start=2):
        if len(r) > 1 and str(r[1]).strip() == term:
            return i, str(r[0]).strip(), r
    for i, r in enumerate(rows[1:], start=2):
        if len(r) > 1 and norm(r[1]) == norm(term):
            return i, str(r[0]).strip(), r
    return None, None, None


def post(env, payload, dry_run=False):
    payload = dict(payload, token=env["GAS_TOKEN"])
    if dry_run:
        shown = dict(payload, token="***")
        print("  [dry-run] POST " + json.dumps(shown, ensure_ascii=False)[:500])
        return {"ok": True, "dry_run": True}
    req = urllib.request.Request(env["GAS_WEBAPP_URL"],
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=90).read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser(description="記事MDを用語DBに反映する")
    ap.add_argument("md", help="drafts/{用語}.md")
    ap.add_argument("--doc-url", required=True, help="Doc化で作ったGoogleドキュメントのURL")
    ap.add_argument("--term", help="用語DBのB列と照合する用語名（既定はファイル名）")
    ap.add_argument("--regenerated-from", help="作り直しのとき、元のレシピ版（例: v0）")
    ap.add_argument("--old-doc-url", help="作り直しのとき、前の版のDoc URL")
    ap.add_argument("--context", default="", help="新規行を作るときの補足・文脈")
    ap.add_argument("--dry-run", action="store_true", help="送信内容を出すだけで書き込まない")
    args = ap.parse_args()

    env = load_env()
    if not args.dry_run and (not env.get("GAS_WEBAPP_URL") or not env.get("GAS_TOKEN")):
        sys.exit(".env に GAS_WEBAPP_URL / GAS_TOKEN が無い")

    path = Path(args.md)
    if not path.is_absolute():
        path = BASE / args.md
    if not path.exists():
        sys.exit(f"見つからない: {args.md}")

    fm = read_frontmatter(path)
    term = args.term or path.stem
    stamped = fm.get("creator_version", "")
    if not stamped:
        print("警告: レシピ版が刻まれていない。先に stamp_version.py を実行しておくこと", file=sys.stderr)
    elif not args.regenerated_from:
        # 生成したてなのに旧版が刻まれているのは、たいてい --backfill の当て間違い。
        # 気づかず登録すると、その記事は最初から「作り直し対象」として扱われてしまう。
        try:
            sys.path.insert(0, str(BASE / "scripts"))
            from recipe_version import state as recipe_state
            current = recipe_state()["version"]
            if stamped != current:
                print(f"警告: この記事は {stamped} と刻まれているが、いまのレシピは {current}。", file=sys.stderr)
                print(f'  いま生成した記事なら刻み直す: python3 scripts/stamp_version.py "{args.md}"',
                      file=sys.stderr)
        except Exception:
            pass

    rows = read_sheet()
    row_no, gid, row = find_row(rows, term)
    if gid:
        print(f"用語DB: {gid}（{row_no}行目）に反映する")
    else:
        print(f"用語DB: 「{term}」が見つからないので新しい行を作る")
        res = post(env, {"action": "add_term", "silent": True, "term": term,
                         "context": args.context, "proposer": "article-creator",
                         "note": "記事生成時に自動追加"}, args.dry_run)
        if not res.get("ok"):
            sys.exit(f"add_term に失敗: {res}")
        gid = res.get("id", "G-???")
        row = None
        print(f"  → {gid} を追加した")

    prev_status = str(row[7]).strip() if row and len(row) > 7 else ""

    payload = {
        "action": "update_row",
        "id": gid,
        "doc_url": args.doc_url,
        "generated_at": date.today().isoformat(),
        "slug": fm.get("slug", ""),
        "excerpt": fm.get("excerpt", ""),
        "eyecatch_prompt": fm.get("eyecatch_prompt", ""),
        "creator_version": fm.get("creator_version", ""),
        "recipe_hash": fm.get("recipe_hash", ""),
        "flag": False,
    }
    if fm.get("category_id"):
        payload["category_id"] = fm["category_id"]
    if fm.get("wp_post_id"):
        payload["wp_post_id"] = fm["wp_post_id"]
    if fm.get("featured_media"):
        payload["featured_media"] = fm["featured_media"]

    if args.regenerated_from:
        # 公開中の本文は旧版のままなので、公開済みの行は「レビュー待ち」に戻さない
        payload["status"] = "作り直し済み" if prev_status == PUBLISHED else "レビュー待ち"
        payload["regen"] = False
        payload["regen_note"] = (f"{date.today().isoformat()} {args.regenerated_from} → "
                                 f"{fm.get('creator_version', '')} で作り直し")
        if args.old_doc_url:
            payload["note"] = f"旧版{args.regenerated_from}: {args.old_doc_url}"
    else:
        payload["status"] = "レビュー待ち"

    res = post(env, payload, args.dry_run)
    if not res.get("ok"):
        sys.exit(f"update_row に失敗: {res}")

    print(f"完了: {gid} / status={payload['status']} / {args.doc_url}")
    if args.regenerated_from and prev_status == PUBLISHED:
        print("公開中の記事なので、WPへの反映は中身を確認してから "
              f"「@用語くん {term} をWP下書きに」で進めること")
    return 0


if __name__ == "__main__":
    sys.exit(main())
