#!/usr/bin/env python3
"""drafts/{用語}.md から「Googleドキュメントに貼る版」のMDを組み立てる。

Doc化のたびに手作業でフロントマターを外してタイトルと案内行を足していたので、
版の記載が抜けたり、案内行の文面がDocごとにぶれたりしていた。ここで組み立てを
1か所にまとめ、**どのDocを開いても、どのレシピ版で作られたかが分かる**ようにする。

出力の冒頭は必ずこの形になる:

    # {タイトル}

    *（レビュー用ドラフト：…）*

    *（版：v15 ／ レシピhash 7fe2c26a0557 ／ 生成日 2026-09-07 ／ この行はレビュー用で、WordPressには載りません）*

版の値はフロントマターの creator_version / recipe_hash / generated_at を読む。
これらは scripts/stamp_version.py が刻む。刻まれていなければエラーで止める
（版が分からないまま Doc を作らせないための門番）。

使い方:
    python3 scripts/make_doc_md.py "drafts/恒常的注意力分散.md"
        pipeline/doc-ready/恒常的注意力分散.md に書き出し、パスを表示する
    python3 scripts/make_doc_md.py "drafts/OOUX.md" --old-doc-url "https://docs.google.com/..."
        作り直しのとき、旧Docへのリンク行を足す
    python3 scripts/make_doc_md.py "drafts/OOUX.md" --stdout
        ファイルに書かず標準出力に出す（そのまま create_file に渡したいとき）
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stamp_version import split_frontmatter, read_key  # noqa: E402
from recipe_version import BASE  # noqa: E402

DOC_READY = BASE / "pipeline" / "doc-ready"

REVIEW_NOTE = (
    "*（レビュー用ドラフト：本文を直接編集してください。"
    "英字¥カタカナ¥ は読みがな記法、-- wp分割ライン-- は投稿時の区切りマーカーなので、"
    "そのまま残してください）*"
)

# 版の行はこの書き出しで固定する。あとからDoc→MDへ戻す処理を足すときに、
# 前方一致で確実に取り除けるようにするため。
VERSION_PREFIX = "*（版："


def args_file_hint(md_path: Path):
    """エラーメッセージに載せるパス。リポジトリ配下なら相対にして貼り付けやすくする。"""
    try:
        return md_path.relative_to(BASE)
    except ValueError:
        return md_path


def build_version_line(version, recipe_hash, generated_at, regenerated_from=None):
    parts = [f"版：{version}"]
    if recipe_hash:
        parts.append(f"レシピhash {recipe_hash}")
    if generated_at:
        parts.append(f"生成日 {generated_at}")
    if regenerated_from:
        parts.append(f"{regenerated_from} から作り直し")
    parts.append("この行はレビュー用で、WordPressには載りません")
    return "*（" + " ／ ".join(parts) + "）*"


def build(md_path: Path, old_doc_url=None):
    text = md_path.read_text(encoding="utf-8")
    parts = split_frontmatter(text)
    if parts is None:
        sys.exit(f"フロントマターが無い: {md_path}")
    _, fm, body = parts

    version = read_key(fm, "creator_version")
    if not version:
        sys.exit(
            f"creator_version が刻まれていない: {md_path}\n"
            f'  先に版を刻む: python3 scripts/stamp_version.py "{args_file_hint(md_path)}"'
        )

    title = read_key(fm, "title") or md_path.stem
    version_line = build_version_line(
        version,
        read_key(fm, "recipe_hash"),
        read_key(fm, "generated_at"),
        read_key(fm, "regenerated_from"),
    )

    head = [f"# {title}", "", REVIEW_NOTE, "", version_line]
    if old_doc_url:
        head += ["", f"*（{version} で作り直した版です。前の版はこちら: {old_doc_url}）*"]

    # body は "---" 行から始まるので、閉じの1行を落として本文だけにする
    body_lines = body.split("\n")
    if body_lines and body_lines[0].strip() == "---":
        body_lines = body_lines[1:]
    body_text = "\n".join(body_lines).lstrip("\n")

    return "\n".join(head) + "\n\n" + body_text


def main():
    ap = argparse.ArgumentParser(description="Doc貼り付け用のMDを組み立てる")
    ap.add_argument("file", help="対象のMD（例: drafts/恒常的注意力分散.md）")
    ap.add_argument("--old-doc-url", help="作り直しのとき、前の版のDoc URL")
    ap.add_argument("--stdout", action="store_true", help="ファイルに書かず標準出力に出す")
    ap.add_argument("--out", help="出力先を明示する（既定は pipeline/doc-ready/{用語}.md）")
    args = ap.parse_args()

    md_path = Path(args.file)
    if not md_path.is_absolute():
        md_path = BASE / args.file
    if not md_path.exists():
        sys.exit(f"見つからない: {args.file}")

    doc_md = build(md_path, args.old_doc_url)

    if args.stdout:
        print(doc_md, end="")
        return 0

    out = Path(args.out) if args.out else DOC_READY / md_path.name
    if not out.is_absolute():
        out = BASE / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc_md, encoding="utf-8")
    print(f"書き出した: {out.relative_to(BASE)}")
    print(doc_md.split("\n")[4])  # 版の行を目視できるように出す
    return 0


if __name__ == "__main__":
    sys.exit(main())
