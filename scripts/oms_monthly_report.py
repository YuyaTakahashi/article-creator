#!/usr/bin/env python3
"""OMS課金 調整額の月次レポートと Slack 報告文ドラフトを作る。

verify_oms_adjustment.py が出した JSON と各シートを読み、
あとから誰でも追える月次レポート（Markdown）と、登録完了連絡の下書きを生成する。

使い方:
    python3 scripts/oms_monthly_report.py \
        --term 2026-07 \
        --report work/2026-07/report.json \
        --master work/2026-07/master.tsv \
        --target-data work/2026-07/target_data.tsv \
        --create-csv work/2026-07/create_csv.tsv \
        --prev-create-csv work/2026-06/create_csv.tsv \
        --out-report work/2026-07/monthly_report.md \
        --out-slack work/2026-07/slack_draft.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from verify_oms_adjustment import (  # noqa: E402
    load_master,
    read_create_csv,
    read_table,
    term_bounds,
    to_int,
)


def jp_term(term: str) -> str:
    year, month = term.split("-")
    return f"{year}年{int(month)}月"


def build_rows(
    csv_rows: list[dict[str, str]],
    target_rows: list[dict[str, str]],
    prev_rows: list[dict[str, str]],
    master_by_code: dict,
) -> list[dict]:
    shipment_by_acc = {
        r.get("acc", "").strip(): to_int(r.get("shipment_cnt", "")) for r in target_rows if r.get("acc", "").strip()
    }
    prev_by_acc = {
        r.get("acc", "").strip(): to_int(r.get("amount", "")) or 0 for r in prev_rows if r.get("acc", "").strip()
    }

    rows = []
    for r in csv_rows:
        acc = r.get("acc", "").strip()
        if not acc:
            continue
        amount = to_int(r.get("amount", "")) or 0
        prev = prev_by_acc.get(acc)
        master = master_by_code.get(acc)
        rows.append(
            {
                "acc": acc,
                "nickname": master.nickname if master else "（master になし）",
                "shipment": shipment_by_acc.get(acc),
                "amount": amount,
                "prev": prev,
                "delta": None if prev is None else amount - prev,
                "bill_start": master.bill_start if master else None,
                "bill_end": master.bill_end if master else None,
            }
        )
    rows.sort(key=lambda x: -x["amount"])
    return rows, prev_by_acc


def yen(value: int | None) -> str:
    return "—" if value is None else f"{value:,}"


def signed_yen(value: int | None) -> str:
    if value is None:
        return "新規"
    if value == 0:
        return "±0"
    return f"{value:+,}"


def render_report(term: str, report: dict, rows: list[dict], prev_by_acc: dict[str, int]) -> str:
    stats = report.get("stats", {})
    summary = report.get("summary", {})
    findings = report.get("findings", [])
    total = sum(r["amount"] for r in rows)
    prev_total = sum(prev_by_acc.values())
    prev_count = len(prev_by_acc)

    added = [r for r in rows if r["prev"] is None]
    removed = sorted(set(prev_by_acc) - {r["acc"] for r in rows})

    lines = [
        f"# OMS課金 調整額 月次レポート {jp_term(term)}分",
        "",
        f"- 対象月: {term}（{jp_term(term)}の出荷実績にもとづく請求）",
        f"- 作成日: {dt.date.today().isoformat()}",
        f"- 自動チェック判定: **{summary.get('verdict', '不明')}**"
        f"（BLOCKER {summary.get('blocker', 0)} / WARN {summary.get('warn', 0)}）",
        "",
        "## サマリー",
        "",
        "| 項目 | 前月 | 当月 | 差分 |",
        "| --- | ---: | ---: | ---: |",
        f"| 請求社数 | {prev_count}社 | {len(rows)}社 | {len(rows) - prev_count:+d}社 |",
        f"| 請求総額（税抜） | {yen(prev_total)}円 | {yen(total)}円 | {signed_yen(total - prev_total)}円 |",
        f"| 1社あたり平均 | {yen(prev_total // prev_count) if prev_count else '—'}円 "
        f"| {yen(total // len(rows)) if rows else '—'}円 | |",
    ]

    if "billing_candidate_count" in stats:
        lines.append(
            f"| 課金候補（条件は満たすが未合意） | — | {stats['billing_candidate_count']}社 | |"
        )
    lines += ["", "## 荷主別の内訳", "", "| 荷主コード | 荷主名 | 出荷件数 | 当月請求額 | 前月請求額 | 差分 |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for r in rows:
        lines.append(
            f"| {r['acc']} | {r['nickname']} | {yen(r['shipment'])} | {yen(r['amount'])} "
            f"| {yen(r['prev'])} | {signed_yen(r['delta'])} |"
        )
    lines.append(f"| **合計** | **{len(rows)}社** | | **{yen(total)}** | **{yen(prev_total)}** | **{signed_yen(total - prev_total)}** |")

    lines += ["", "## 当月の出入り", ""]
    if added:
        lines.append("### 新規に請求を開始した荷主")
        lines.append("")
        for r in added:
            lines.append(f"- {r['acc']} {r['nickname']}（請求開始日 {r['bill_start'] or '不明'} / {yen(r['amount'])}円）")
        lines.append("")
    else:
        lines += ["### 新規に請求を開始した荷主", "", "- なし", ""]

    lines.append("### 当月から請求対象外になった荷主")
    lines.append("")
    if removed:
        for acc in removed:
            lines.append(f"- {acc}（前月 {yen(prev_by_acc[acc])}円）")
    else:
        lines.append("- なし")
    lines.append("")

    blockers = [f for f in findings if f["severity"] == "BLOCKER"]
    warns = [f for f in findings if f["severity"] == "WARN"]

    lines += ["## 自動チェックの指摘", ""]
    lines.append("### 投入前に解消が必要（BLOCKER）")
    lines.append("")
    if blockers:
        for f in blockers:
            lines.append(f"- `{f['check']}` {f['acc'] or '-'}: {f['message']}")
    else:
        lines.append("- なし")
    lines += ["", "### 人による確認が必要（WARN）", ""]
    if warns:
        for f in warns:
            lines.append(f"- `{f['check']}` {f['acc'] or '-'}: {f['message']}")
    else:
        lines.append("- なし")

    lines += [
        "",
        "## 人による確認の記録",
        "",
        "この欄は投入担当と確認担当が手で埋める。",
        "",
        "| 項目 | 内容 |",
        "| --- | --- |",
        "| CSV生成・チェック実施者 | |",
        "| Admin へのCSV投入者 | |",
        "| 投入日時 | |",
        "| ダブルチェック担当 | |",
        "| ダブルチェック結果 | |",
        "| Slack報告 | |",
        "| 備考（WARNへの対応など） | |",
        "",
        "## 参照",
        "",
        "- 調整額生成ツール（スプレッドシート）",
        "- 請求ロジック詳細（O-musubi PJドキュメント）",
        "- 投入した調整額CSVは同じフォルダに保管する",
    ]
    return "\n".join(lines) + "\n"


def render_slack(term: str, report: dict, rows: list[dict], prev_by_acc: dict[str, int]) -> str:
    summary = report.get("summary", {})
    total = sum(r["amount"] for r in rows)
    prev_total = sum(prev_by_acc.values())
    prev_count = len(prev_by_acc)
    blockers = summary.get("blocker", 0)
    warns = summary.get("warn", 0)

    head = f"OMS課金（受注在庫一元化システム利用料）{jp_term(term)}分の調整額を登録しました。"
    if blockers:
        head = (
            f"【未登録・確認中】OMS課金 {jp_term(term)}分の調整額について、"
            f"自動チェックで {blockers}件 の要修正が出ているため登録を保留しています。"
        )

    lines = [
        "（Slack 報告文ドラフト。送信前に必ず内容を確認すること）",
        "",
        "---",
        "",
        head,
        "",
        f"・対象月: {jp_term(term)}出荷分",
        f"・請求社数: {len(rows)}社（前月 {prev_count}社 / {len(rows) - prev_count:+d}社）",
        f"・請求総額: {total:,}円（税抜、前月 {prev_total:,}円 / {total - prev_total:+,}円）",
    ]

    added = [r for r in rows if r["prev"] is None]
    removed = sorted(set(prev_by_acc) - {r["acc"] for r in rows})
    if added:
        lines.append("・新規: " + "、".join(f"{r['acc']} {r['nickname']}" for r in added))
    if removed:
        lines.append("・請求終了: " + "、".join(removed))
    if warns:
        lines.append(f"・確認事項: {warns}件（詳細は月次レポート参照）")

    lines += [
        "",
        "詳細は月次レポートをご確認ください。",
        "月次レポート: <レポートのURLを貼る>",
        "調整額の登録先: <Admin の調整額一覧URLを貼る>",
        "",
        "内容のダブルチェックをお願いします。",
        "",
        "---",
        "",
        "送信前チェック:",
        "- [ ] 宛先チャンネルは合っているか",
        "- [ ] 社数・総額が月次レポートと一致しているか",
        "- [ ] URL を実際のものに差し替えたか",
        "- [ ] 15時までに送れるか",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OMS課金 調整額の月次レポートと Slack 下書きを作る")
    ap.add_argument("--term", required=True, help="対象月 YYYY-MM")
    ap.add_argument("--report", required=True, help="verify_oms_adjustment.py が出力した JSON")
    ap.add_argument("--master", required=True)
    ap.add_argument("--target-data", required=True)
    ap.add_argument("--create-csv", required=True)
    ap.add_argument("--prev-create-csv", help="前月の調整額CSV（なければ前月比は空欄になる）")
    ap.add_argument("--out-report", required=True, help="月次レポート Markdown の出力先")
    ap.add_argument("--out-slack", help="Slack 報告文ドラフトの出力先")
    args = ap.parse_args(argv)

    term_bounds(args.term)  # 形式の妥当性を確認する

    with open(args.report, encoding="utf-8") as fh:
        report = json.load(fh)

    master_by_code = {m.code: m for m in load_master(args.master)}
    csv_rows = read_create_csv(args.create_csv)
    target_rows = read_table(args.target_data)
    prev_rows = read_create_csv(args.prev_create_csv) if args.prev_create_csv else []

    rows, prev_by_acc = build_rows(csv_rows, target_rows, prev_rows, master_by_code)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_report)), exist_ok=True)
    with open(args.out_report, "w", encoding="utf-8") as fh:
        fh.write(render_report(args.term, report, rows, prev_by_acc))
    print(f"月次レポート: {args.out_report}")

    if args.out_slack:
        with open(args.out_slack, "w", encoding="utf-8") as fh:
            fh.write(render_slack(args.term, report, rows, prev_by_acc))
        print(f"Slack下書き  : {args.out_slack}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
