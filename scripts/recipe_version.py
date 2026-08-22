#!/usr/bin/env python3
"""article-creator のレシピ（記事の書きぶりを決めるプロンプト群）のバージョンを管理する。

レシピは prompts/recipe-manifest.txt に並んだファイル群を指す。それらの sha256 を束ねて
1 つの版番号（v1, v2, ...）に対応づけ、prompts/recipe.lock.json に記録する。
記事側には scripts/stamp_version.py がこの版番号を刻む。

使い方:
    python3 scripts/recipe_version.py current [--json]
        いまのレシピの版番号とハッシュを出す。lock と中身がずれていれば "v2+dirty" と出す。
    python3 scripts/recipe_version.py check
        ずれていれば exit 1（バージョンの上げ忘れ検知）。git hook とバッチが使う。
    python3 scripts/recipe_version.py bump --note "変更内容の1行説明" [--version v5]
        版を1つ上げ、lock と CHANGELOG.md を更新する。
    python3 scripts/recipe_version.py files
        レシピ構成ファイルと個別ハッシュを一覧する。

"+dirty" について:
    レシピを編集したのに bump していない状態を指す。この状態で生成された記事には
    "v2+dirty" が刻まれる。あとから「どの版で作ったか」を偽らないための仕組みで、
    bump すれば以降の記事はきれいな版番号になる。
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MANIFEST = BASE / "prompts" / "recipe-manifest.txt"
LOCK = BASE / "prompts" / "recipe.lock.json"
VERSION_FILE = BASE / "prompts" / "VERSION"
CHANGELOG = BASE / "prompts" / "CHANGELOG.md"

# .agent/skills（symlink・実体は ~/.claude/skills）を正とし、リポジトリ内の複製を追随させる。
SKILL_MIRRORS = {
    ".agent/skills/article-creator/SKILL.md": "cowork-skills/article-creator/SKILL.md",
    ".agent/skills/article-review/SKILL.md": "cowork-skills/article-review/SKILL.md",
}


def read_manifest():
    if not MANIFEST.exists():
        sys.exit(f"レシピ構成ファイルが無い: {MANIFEST}")
    paths = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            paths.append(line)
    if not paths:
        sys.exit(f"レシピ構成ファイルが空: {MANIFEST}")
    return paths


def file_hash(rel):
    p = BASE / rel
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()


def compute():
    """レシピの実体を読んで {rel: sha256} と束ねハッシュを返す。"""
    files = {}
    for rel in read_manifest():
        files[rel] = file_hash(rel)
    joined = "\n".join(f"{rel}:{files[rel] or 'MISSING'}" for rel in sorted(files))
    combined = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return files, combined


def load_lock():
    if not LOCK.exists():
        return None
    return json.loads(LOCK.read_text(encoding="utf-8"))


def state():
    """いまの状態を1つの辞書にまとめる。他のスクリプトはこれだけ見ればよい。"""
    files, combined = compute()
    lock = load_lock()
    locked_version = (lock or {}).get("version", "v0")
    locked_hash = (lock or {}).get("hash", "")
    locked_files = (lock or {}).get("files", {})

    changed = []
    for rel, h in files.items():
        if h is None:
            changed.append(f"{rel}（ファイルが無い）")
        elif locked_files.get(rel) != h:
            changed.append(rel if rel in locked_files else f"{rel}（レシピに追加）")
    for rel in locked_files:
        if rel not in files:
            changed.append(f"{rel}（レシピから除外）")

    dirty = combined != locked_hash
    return {
        "version": locked_version + ("+dirty" if dirty else ""),
        "clean_version": locked_version,
        "hash": combined[:12],
        "full_hash": combined,
        "dirty": dirty,
        "locked_hash": locked_hash[:12],
        "changed": sorted(changed),
        "files": files,
        "initialized": lock is not None,
    }


def next_version(cur):
    try:
        return "v" + str(int(str(cur).lstrip("v")) + 1)
    except ValueError:
        return "v1"


def sync_skill_mirrors():
    """symlink 側（正）の SKILL.md をリポジトリ内の複製へコピーし、二重管理のズレを潰す。"""
    synced = []
    for src_rel, dst_rel in SKILL_MIRRORS.items():
        src, dst = BASE / src_rel, BASE / dst_rel
        if not src.exists() or not dst.exists():
            continue
        if src.read_bytes() != dst.read_bytes():
            shutil.copyfile(src, dst)
            synced.append(dst_rel)
    return synced


def cmd_current(args):
    st = state()
    if args.json:
        print(json.dumps({k: st[k] for k in
                          ("version", "clean_version", "hash", "full_hash", "dirty", "changed")},
                         ensure_ascii=False))
        return 0
    print(f"{st['version']} {st['hash']}")
    if st["dirty"]:
        print("※ レシピを編集したのに版を上げていない（+dirty）。"
              "確定するには: python3 scripts/recipe_version.py bump --note \"変更内容\"",
              file=sys.stderr)
        for c in st["changed"]:
            print(f"   - {c}", file=sys.stderr)
    return 0


def cmd_check(args):
    st = state()
    if not st["initialized"]:
        print("recipe.lock.json が無い。初回は bump --note \"初版\" で作る。", file=sys.stderr)
        return 1
    if not st["dirty"]:
        print(f"OK: レシピは {st['clean_version']}（{st['hash']}）のまま")
        return 0
    print(f"NG: レシピが {st['clean_version']} から変わっているのに版が上がっていない", file=sys.stderr)
    for c in st["changed"]:
        print(f"   - {c}", file=sys.stderr)
    print('   → python3 scripts/recipe_version.py bump --note "変更内容の1行説明"', file=sys.stderr)
    return 1


def cmd_files(args):
    st = state()
    for rel, h in st["files"].items():
        mark = "欠落" if h is None else h[:12]
        print(f"{mark}  {rel}")
    return 0


def cmd_bump(args):
    synced = sync_skill_mirrors()
    st = state()
    if not st["dirty"] and st["initialized"] and not args.force:
        print(f"レシピは {st['clean_version']} から変わっていない。上げる必要はない（強制するなら --force）")
        return 0

    missing = [rel for rel, h in st["files"].items() if h is None]
    if missing:
        print("レシピ構成ファイルが見つからない: " + ", ".join(missing), file=sys.stderr)
        return 1

    new_version = args.version or (next_version(st["clean_version"]) if st["initialized"] else "v1")
    today = date.today().isoformat()
    files, combined = compute()

    LOCK.write_text(json.dumps({
        "version": new_version,
        "hash": combined,
        "updated_at": today,
        "note": args.note,
        "files": files,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    VERSION_FILE.write_text(new_version + "\n", encoding="utf-8")

    changed_lines = "\n".join(f"  - {c}" for c in st["changed"]) or "  - （初版）"
    entry = (f"## {new_version} — {today}\n\n"
             f"{args.note}\n\n"
             f"レシピhash: `{combined[:12]}`\n\n"
             f"変更されたファイル:\n{changed_lines}\n\n")
    if CHANGELOG.exists():
        old = CHANGELOG.read_text(encoding="utf-8")
        head, _, rest = old.partition("\n## ")
        body = ("\n## " + rest) if rest else ""
        CHANGELOG.write_text(head.rstrip("\n") + "\n\n" + entry + body.lstrip("\n"), encoding="utf-8")
    else:
        CHANGELOG.write_text(
            "# article-creator レシピ変更履歴\n\n"
            "記事の書きぶりを決めるプロンプト群（prompts/recipe-manifest.txt）の変更履歴。\n"
            "各記事のフロントマター `creator_version` はここの版番号を指す。\n\n" + entry,
            encoding="utf-8")

    if synced:
        print("複製を同期した: " + ", ".join(synced))
    print(f"{st['clean_version']} → {new_version}（{combined[:12]}）")
    print(f"記録先: prompts/VERSION / prompts/recipe.lock.json / prompts/CHANGELOG.md")
    return 0


def main():
    ap = argparse.ArgumentParser(description="article-creator レシピのバージョン管理")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("current", help="いまの版番号とハッシュを出す")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_current)

    p = sub.add_parser("check", help="版の上げ忘れを検知する（ずれていれば exit 1）")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("files", help="レシピ構成ファイルと個別ハッシュを一覧する")
    p.set_defaults(func=cmd_files)

    p = sub.add_parser("bump", help="版を1つ上げる")
    p.add_argument("--note", required=True, help="何を変えたかの1行説明")
    p.add_argument("--version", help="版番号を明示指定する（既定は +1）")
    p.add_argument("--force", action="store_true", help="変更が無くても上げる")
    p.set_defaults(func=cmd_bump)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
