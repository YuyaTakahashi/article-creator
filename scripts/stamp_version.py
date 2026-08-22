#!/usr/bin/env python3
"""生成した記事MDのフロントマターに「どのレシピ版で作ったか」を刻む。

article-creator は日々プロンプトを直すので、記事だけ見ても当時の書きぶりが分からなくなる。
生成直後にこれを走らせて creator_version / recipe_hash / generated_at を残し、
あとから「この記事は v2 のレシピだから作り直す」と判断できるようにする。

使い方:
    python3 scripts/stamp_version.py drafts/モーダル.md
    python3 scripts/stamp_version.py drafts/モーダル.md --regenerated-from v2
    python3 scripts/stamp_version.py --show drafts/モーダル.md
    python3 scripts/stamp_version.py --backfill
        既存の drafts/*.md のうち未記録のものに creator_version: "v0" を付ける
        （v0 = バージョン管理を始める前に作られた記事）
    python3 scripts/stamp_version.py --list
        drafts/*.md の版を一覧し、最新版でないものを出す
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recipe_version import state, BASE  # noqa: E402

DRAFTS = BASE / "drafts"
STAMP_KEYS = ("creator_version", "recipe_hash", "generated_at", "regenerated_from")


def split_frontmatter(text):
    """(前置き, フロントマター行list, 本文) に割る。フロントマターが無ければ None。"""
    if not text.startswith("---"):
        return None
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[0], lines[1:i], "\n".join(lines[i:])
    return None


def read_key(fm_lines, key):
    pat = re.compile(r"^" + re.escape(key) + r"\s*:\s*(.*)$")
    for line in fm_lines:
        m = pat.match(line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def set_keys(fm_lines, values):
    """既存キーは置換、無いキーはフロントマター末尾に追記する。行の順序と書式は保つ。"""
    out = list(fm_lines)
    for key, val in values.items():
        if val is None:
            continue
        line = f'{key}: "{val}"'
        pat = re.compile(r"^" + re.escape(key) + r"\s*:")
        for i, cur in enumerate(out):
            if pat.match(cur):
                out[i] = line
                break
        else:
            out.append(line)
    return out


def stamp(path, version, recipe_hash, generated_at, regenerated_from=None, only_if_missing=False):
    text = path.read_text(encoding="utf-8")
    parts = split_frontmatter(text)
    if parts is None:
        return f"skip（フロントマターが無い）: {path.name}"
    head, fm, body = parts

    if only_if_missing and read_key(fm, "creator_version"):
        return None

    values = {"creator_version": version, "recipe_hash": recipe_hash}
    if generated_at:
        values["generated_at"] = generated_at
    if regenerated_from:
        values["regenerated_from"] = regenerated_from

    path.write_text(head + "\n" + "\n".join(set_keys(fm, values)) + "\n" + body, encoding="utf-8")
    label = f"{version}"
    if regenerated_from:
        label += f"（{regenerated_from} から作り直し）"
    return f"{path.name}: {label}"


def show(path):
    parts = split_frontmatter(path.read_text(encoding="utf-8"))
    if parts is None:
        print(f"{path.name}: フロントマターが無い")
        return
    fm = parts[1]
    for k in STAMP_KEYS:
        v = read_key(fm, k)
        if v:
            print(f"{k}: {v}")
    if not read_key(fm, "creator_version"):
        print("creator_version: （未記録）")


def main():
    ap = argparse.ArgumentParser(description="記事MDにレシピ版を刻む")
    ap.add_argument("files", nargs="*", help="対象のMDファイル")
    ap.add_argument("--regenerated-from", help="作り直し元の版（例: v2）")
    ap.add_argument("--generated-at", help="生成日（既定は今日）")
    ap.add_argument("--backfill", action="store_true", help="未記録の既存記事に v0 を付ける")
    ap.add_argument("--list", action="store_true", help="drafts/*.md の版を一覧する")
    ap.add_argument("--show", action="store_true", help="指定ファイルの版を表示する")
    args = ap.parse_args()

    st = state()

    if args.show:
        for f in args.files:
            show(Path(f))
        return 0

    if args.list:
        cur = st["version"]
        rows, stale = [], 0
        for p in sorted(DRAFTS.glob("*.md")):
            parts = split_frontmatter(p.read_text(encoding="utf-8"))
            v = read_key(parts[1], "creator_version") if parts else None
            v = v or "（未記録）"
            if v != cur:
                stale += 1
            rows.append((v, p.name))
        for v, name in sorted(rows):
            print(f"{'  ' if v == cur else '旧'} {v:<12} {name}")
        print(f"\n最新版: {cur} / 全 {len(rows)} 本中 {stale} 本が旧版")
        return 0

    if args.backfill:
        done = 0
        for p in sorted(DRAFTS.glob("*.md")):
            r = stamp(p, "v0", "unknown", None, only_if_missing=True)
            if r:
                print(r)
                done += 1
        print(f"\n{done} 本に v0（バージョン管理開始前）を付けた")
        return 0

    if not args.files:
        ap.error("対象ファイルを指定するか --backfill / --list を使う")

    generated_at = args.generated_at or date.today().isoformat()
    for f in args.files:
        p = Path(f)
        if not p.is_absolute():
            p = BASE / f
        if not p.exists():
            print(f"見つからない: {f}", file=sys.stderr)
            return 1
        print(stamp(p, st["version"], st["hash"], generated_at, args.regenerated_from))
    if st["dirty"]:
        print("※ レシピが未確定（+dirty）のまま刻んだ。"
              'bump しておくと版が読みやすくなる: python3 scripts/recipe_version.py bump --note "..."',
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
