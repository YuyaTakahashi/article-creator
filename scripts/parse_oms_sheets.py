#!/usr/bin/env python3
"""O-musubi_調整額生成ツールの読み取り結果を、シートごとの TSV に分解する。

Google Drive MCP の read_file_content は、スプレッドシートの全シートを
Markdown のテーブルとして連結した1つのテキストで返す。そのままでは検証に使えないため、
シートを見分けて TSV に切り出す。

入力は次のいずれでもよい。
  * MCP の結果 JSON（{"fileContent": "..."} 形式）
  * 上記から取り出した Markdown テキスト

使い方:
    python3 scripts/parse_oms_sheets.py --input dump.json --outdir work/2026-07

出力（見つかったものだけ）:
    master.tsv / target_data.tsv / create_csv.tsv / bill_adjustments.tsv / unit_price.tsv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

# シート名 -> (ヘッダ行に必ず含まれる列名の集合)
SIGNATURES: list[tuple[str, set[str]]] = [
    ("master", {"code", "規約合意日", "請求開始日"}),
    ("target_data", {"acc", "shipment_cnt", "target_term"}),
    ("create_csv", {"acc", "warehouseBaseCode", "targetDate", "amount", "memo"}),
    ("bill_adjustments", {"code", "target_date", "amount", "memo"}),
    ("unit_price", {"-500", "501-5000", "20000-"}),
]


def unescape(cell: str) -> str:
    """Markdown テーブル向けのエスケープを戻す。"""
    for before, after in (
        ("&#10;", "\n"),
        ("\\_", "_"),
        ("\\!", "!"),
        ("\\~", "~"),
        ("\\&", "&"),
        ("\\-", "-"),
        ("\\|", "|"),
        ("\\*", "*"),
        ("\\[", "["),
        ("\\]", "]"),
        ("\\\\", "\\"),
    ):
        cell = cell.replace(before, after)
    return cell.strip()


def split_row(line: str) -> list[str]:
    return [unescape(c) for c in line.split("|")[1:-1]]


def is_separator(line: str) -> bool:
    cells = [c.strip() for c in line.split("|")[1:-1]]
    return bool(cells) and all(set(c) <= set(":- ") and "-" in c for c in cells)


def load_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    stripped = raw.lstrip()
    if stripped.startswith("{"):
        try:
            return json.loads(raw)["fileContent"]
        except (ValueError, KeyError):
            pass
    return raw


def split_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in text.split("\n"):
        if line.strip():
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return [b for b in blocks if any(line.lstrip().startswith("|") for line in b)]


def find_header(block: list[str]) -> tuple[int, list[str]] | None:
    """ブロックの先頭数行からヘッダ行を探す。

    create_csv シートは1行目が【必須】の説明文、2行目が実際の列名なので、
    署名に一致する行が見つかるまで数行ぶん試す。
    """
    candidates = [i for i, line in enumerate(block) if line.lstrip().startswith("|") and not is_separator(line)]
    for idx in candidates[:4]:
        cells = set(split_row(block[idx]))
        for name, signature in SIGNATURES:
            if signature <= cells:
                return idx, split_row(block[idx])
    return None


def identify(header: list[str]) -> str | None:
    cells = set(header)
    for name, signature in SIGNATURES:
        if signature <= cells:
            return name
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="調整額生成ツールの読み取り結果をシートごとの TSV に分解する")
    ap.add_argument("--input", required=True, help="MCP の結果 JSON、または Markdown テキスト")
    ap.add_argument("--outdir", required=True, help="TSV の出力先ディレクトリ")
    args = ap.parse_args(argv)

    os.makedirs(args.outdir, exist_ok=True)
    text = load_text(args.input)

    written: dict[str, int] = {}
    for block in split_blocks(text):
        found = find_header(block)
        if found is None:
            continue
        header_idx, header = found
        name = identify(header)
        if name is None or name in written:
            continue

        rows = [header]
        for line in block[header_idx + 1 :]:
            if not line.lstrip().startswith("|") or is_separator(line):
                continue
            cells = split_row(line)
            cells += [""] * (len(header) - len(cells))
            rows.append(cells[: len(header)])

        path = os.path.join(args.outdir, f"{name}.tsv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, delimiter="\t")
            for row in rows:
                writer.writerow([c.replace("\n", " ").replace("\t", " ") for c in row])
        written[name] = len(rows) - 1

    if not written:
        print("シートを1つも認識できなかった。入力が調整額生成ツールの読み取り結果か確認する。", file=sys.stderr)
        return 1

    for name, count in written.items():
        print(f"{args.outdir}/{name}.tsv  ({count}行)")

    missing = [n for n, _ in SIGNATURES if n not in written and n != "unit_price"]
    if missing:
        print(f"\n見つからなかったシート: {missing}", file=sys.stderr)
        print("スプレッドシートの読み取りが途中で切れている可能性がある。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
