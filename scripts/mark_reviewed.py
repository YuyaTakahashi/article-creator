#!/usr/bin/env python3
"""article-review の実施印 `reviewed_at` を刻み、実施ログを残す。

`reviewed_at` は「人が読める最終形になった」ことを article-post に伝える印である。
これを生成側（article-creator / 各バッチプロンプト）が自己申告で書けてしまうと、
推敲していない初稿がそのまま投稿ゲートを通る。実際に 2026-08-31 の生成では
article-critic も article-review も呼ばれないまま reviewed_at が刻まれていた。

そこで印の発行をこのスクリプトに一本化する。ここを通ると
`logs/review/{slug}-{YYYY-MM-DD}.json` が必ず残り、post_to_wp.py が
「印はあるが実施ログが無い」記事を検出して投稿を止められる。

使い方:
    # article-review の Phase C から呼ぶ
    python3 scripts/mark_reviewed.py "drafts/モーダル.md" \
        --critic-verdict pass --note "提唱年を1981→1983に修正" --fixed "提唱年" --fixed "所属機関"

    # 投稿前ゲートの確認だけ（印と実施ログの整合を見る）
    python3 scripts/mark_reviewed.py --verify "drafts/モーダル.md"
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stamp_version import split_frontmatter, read_key, set_keys  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
REVIEW_LOG_DIR = REPO / "logs" / "review"


def rel(path):
    """リポジトリ相対で見せる。外にあるパスはそのまま返す（表示用なので失敗させない）。"""
    try:
        return path.relative_to(REPO)
    except ValueError:
        return path


def log_key(md_path, fm_lines):
    """ログのファイル名に使う識別子。slug があれば slug、無ければファイル名を使う。"""
    return read_key(fm_lines, "slug") or md_path.stem


def review_logs(md_path, fm_lines):
    """この記事に対する実施ログを新しい順に返す。"""
    if not REVIEW_LOG_DIR.exists():
        return []
    key = log_key(md_path, fm_lines)
    return sorted(REVIEW_LOG_DIR.glob(f"{key}-*.json"), reverse=True)


def verify(md_path):
    """(ok, message) を返す。post_to_wp.py の投稿前ゲートが使う。"""
    parts = split_frontmatter(md_path.read_text(encoding="utf-8"))
    if parts is None:
        return False, "フロントマターが読み取れない"
    fm = parts[1]
    reviewed_at = read_key(fm, "reviewed_at")
    if not reviewed_at:
        return False, (
            "reviewed_at がない（article-review を通していない）。"
            "\n  対処: /article-review " + md_path.name + " を実行する"
        )
    logs = review_logs(md_path, fm)
    if not logs:
        return False, (
            f"reviewed_at: {reviewed_at} が刻まれているが、実施ログが logs/review/ に無い。"
            "\n  生成側が自己申告で書いた印である可能性が高い。"
            "\n  対処: /article-review " + md_path.name + " をあらためて実行する"
        )
    return True, f"reviewed_at: {reviewed_at}（実施ログ: {rel(logs[0])}）"


def mark(md_path, critic_verdict, note, fixed, reviewer):
    text = md_path.read_text(encoding="utf-8")
    parts = split_frontmatter(text)
    if parts is None:
        sys.stderr.write(f"フロントマターが読み取れません: {md_path}\n")
        return 1
    head, fm, body = parts

    today = date.today().isoformat()
    md_path.write_text(
        head + "\n" + "\n".join(set_keys(fm, {"reviewed_at": today})) + "\n" + body,
        encoding="utf-8",
    )

    REVIEW_LOG_DIR.mkdir(parents=True, exist_ok=True)
    key = log_key(md_path, fm)
    log_path = REVIEW_LOG_DIR / f"{key}-{today}.json"
    log_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "file": str(rel(md_path)),
                "title": read_key(fm, "title"),
                "slug": read_key(fm, "slug"),
                "creator_version": read_key(fm, "creator_version"),
                "reviewed_at": today,
                "reviewed_by": reviewer,
                "critic_verdict": critic_verdict,
                "fixed": fixed or [],
                "note": note or "",
                "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"reviewed_at: {today} を刻みました（{md_path.name}）")
    print(f"実施ログ: {rel(log_path)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="article-review の実施印を刻む / 検証する")
    ap.add_argument("file", help="対象のMDファイル（例: drafts/モーダル.md）")
    ap.add_argument("--verify", action="store_true", help="印と実施ログの整合を確認するだけ")
    ap.add_argument("--critic-verdict", default="unknown",
                    help="article-critic の最終判定（pass / regenerate / escalate）")
    ap.add_argument("--note", help="推敲・事実修正の要点を1〜2行で")
    ap.add_argument("--fixed", action="append", help="直した項目（複数指定できる）")
    ap.add_argument("--reviewer", default="article-review", help="実施主体（既定: article-review）")
    args = ap.parse_args()

    md_path = Path(args.file)
    if not md_path.is_absolute():
        md_path = (REPO / args.file).resolve()
    if not md_path.exists():
        sys.stderr.write(f"MDファイルが見つかりません: {md_path}\n")
        return 1

    if args.verify:
        ok, message = verify(md_path)
        print(("OK: " if ok else "NG: ") + message)
        return 0 if ok else 1

    return mark(md_path, args.critic_verdict, args.note, args.fixed, args.reviewer)


if __name__ == "__main__":
    sys.exit(main())
