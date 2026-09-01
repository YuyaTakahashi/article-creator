#!/usr/bin/env python3
"""OMS課金 調整額CSVの検証ツール。

O-musubi_調整額生成ツール（Google スプレッドシート）の各シートを入力に取り、
Admin へ投入する調整額CSVが正しいかを、生成ロジックとは独立に再計算・突合する。

判定は3段階。
  BLOCKER : 投入してはいけない。請求ミスに直結する。
  WARN    : 人間の確認が必要。自動では白黒つけられない。
  INFO    : 記録のみ。前月比などの参考情報。

BLOCKER が1件でもあれば終了コード 1 を返す。

使い方（投入前）:
    python3 scripts/verify_oms_adjustment.py \
        --term 2026-07 \
        --master master.tsv \
        --target-data target_data.tsv \
        --create-csv create_csv.tsv \
        --prev-create-csv prev_create_csv.tsv \
        --json out/report.json

使い方（投入後）:
    python3 scripts/verify_oms_adjustment.py \
        --term 2026-07 \
        --master master.tsv \
        --target-data target_data.tsv \
        --create-csv create_csv.tsv \
        --bill-adjustments bill_adjustments.tsv \
        --json out/report_post.json

入力ファイルは CSV / TSV のどちらでもよい（拡張子で判定し、判別できなければ内容から推定する）。
scripts/parse_oms_sheets.py が MCP のシート読み取り結果からこれらを生成する。
"""

from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
import io
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 料金定義
# ---------------------------------------------------------------------------

FIXED_FEE = 10000

# (下限件数, 上限件数 or None, 単価) — 階段式。件数の「その段に含まれる分」だけに単価がかかる。
TIERS: list[tuple[int, int | None, int]] = [
    (1, 500, 0),
    (501, 5000, 19),
    (5001, 10000, 9),
    (10001, 15000, 5),
    (15001, 20000, 3),
    (20001, None, 1),
]

# target_data シートの段別件数の列名（TIERS と同じ並び）
TIER_COLUMNS = ["-500", "501-5000", "5001-10000", "10001-15000", "15001-20000", "20000-"]

# 課金対象としてカウントするチャネル。
BILLABLE_CHANNELS = {
    "shopify",
    "ecforce",
    "rakuten",
    "yahoo",
    "makeshop",
    "stores",
    "generic_b2c",
    "tiktok",
    "qoo10",
}

# 課金対象としてカウントしないチャネル（旧アーキ・受注連携なし）。
NON_BILLABLE_CHANNELS = {
    "nextengine",
    "amazon",
    "amazon_fba",
}

# master の「連携先EC」だけでは新アーキ／旧アーキを判別できないチャネル。
# 新アーキならカウント対象、旧アーキなら対象外。Admin の (Fraise) 表記でしか区別できない。
UNDETERMINABLE_CHANNELS = {"thebase"}

# Admin の調整額CSVテンプレートの列順。
CSV_COLUMNS = [
    "acc",
    "warehouseBaseCode",
    "targetDate",
    "detailDiv",
    "taxExemptAmount",
    "taxInputDiv",
    "amount",
    "memo",
    "wholesaleDiv",
    "wholesaleValue",
    "staffMemo",
]

# 全行で固定であるべき値。
FIXED_CSV_VALUES = {
    "detailDiv": "0",       # その他
    "taxInputDiv": "0",     # 税抜き
    "wholesaleDiv": "0",    # 分配なし
    "wholesaleValue": "0",
}

MEMO_TITLE = "受注在庫一元化システム利用料"

# 前月比がこの倍率を超えたら INFO ではなく WARN にする。
MOM_AMOUNT_RATIO = 2.0
MOM_AMOUNT_ABS = 50000


# ---------------------------------------------------------------------------
# 検出結果
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    severity: str  # BLOCKER / WARN / INFO
    check: str
    acc: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "check": self.check,
            "acc": self.acc,
            "message": self.message,
            "detail": self.detail,
        }


class Report:
    def __init__(self, term: str) -> None:
        self.term = term
        self.findings: list[Finding] = []
        self.stats: dict[str, Any] = {}

    def add(self, severity: str, check: str, acc: str, message: str, **detail: Any) -> None:
        self.findings.append(Finding(severity, check, acc, message, detail))

    def blocker(self, check: str, acc: str, message: str, **detail: Any) -> None:
        self.add("BLOCKER", check, acc, message, **detail)

    def warn(self, check: str, acc: str, message: str, **detail: Any) -> None:
        self.add("WARN", check, acc, message, **detail)

    def info(self, check: str, acc: str, message: str, **detail: Any) -> None:
        self.add("INFO", check, acc, message, **detail)

    def count(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)

    def to_dict(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
            "summary": {
                "blocker": self.count("BLOCKER"),
                "warn": self.count("WARN"),
                "info": self.count("INFO"),
                "verdict": "NG" if self.count("BLOCKER") else ("要確認" if self.count("WARN") else "OK"),
            },
            "stats": self.stats,
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# 入力の読み込み
# ---------------------------------------------------------------------------


def read_table(path: str, header_row: int = 0) -> list[dict[str, str]]:
    """CSV/TSV を読み、header_row 行目をヘッダとして辞書のリストを返す。"""
    with open(path, encoding="utf-8-sig", newline="") as fh:
        text = fh.read()
    if not text.strip():
        return []
    delimiter = "\t" if text.split("\n", 1)[0].count("\t") >= text.split("\n", 1)[0].count(",") else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) <= header_row:
        return []
    header = [c.strip() for c in rows[header_row]]
    out = []
    for raw in rows[header_row + 1 :]:
        raw = list(raw) + [""] * (len(header) - len(raw))
        out.append({h: raw[i].strip() for i, h in enumerate(header) if h})
    return out


def read_create_csv(path: str) -> list[dict[str, str]]:
    """create_csv シートを読む。1行目が説明文の場合は2行目をヘッダとして扱う。"""
    rows = read_table(path, header_row=0)
    if rows and "acc" in rows[0] and rows[0]["acc"] == "acc":
        # 1行目が【必須】説明行だったので、2行目（列名行）をヘッダに取り直す
        return read_table(path, header_row=1)
    if rows and "acc" not in (rows[0].keys() if rows else {}):
        return read_table(path, header_row=1)
    return rows


def to_int(value: str) -> int | None:
    if value is None:
        return None
    cleaned = re.sub(r"[,\s¥円]", "", str(value)).strip().strip('"')
    if cleaned in ("", "-"):
        return None
    try:
        return int(cleaned)
    except ValueError:
        try:
            f = float(cleaned)
        except ValueError:
            return None
        return int(f) if f.is_integer() else None


def parse_date(value: str) -> dt.date | None:
    if not value:
        return None
    cleaned = str(value).strip().strip('"').strip()
    if not cleaned:
        return None
    cleaned = cleaned.split(" ")[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return dt.datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def split_list(value: str) -> list[str]:
    if not value:
        return []
    return [v.strip().strip('"') for v in str(value).split(",")]


def term_bounds(term: str) -> tuple[dt.date, dt.date]:
    year, month = (int(x) for x in term.split("-"))
    last = calendar.monthrange(year, month)[1]
    return dt.date(year, month, 1), dt.date(year, month, last)


# ---------------------------------------------------------------------------
# 料金計算
# ---------------------------------------------------------------------------


def split_tiers(shipment_cnt: int) -> list[int]:
    """出荷件数を階段式の各段に配分する。"""
    out = []
    for lower, upper, _price in TIERS:
        if upper is None:
            out.append(max(shipment_cnt - (lower - 1), 0))
        else:
            capacity = upper - lower + 1
            out.append(min(max(shipment_cnt - (lower - 1), 0), capacity))
    return out


def calc_amount(shipment_cnt: int) -> tuple[int, list[int]]:
    """出荷件数から請求額を計算する。戻り値は (合計額, 段別件数)。"""
    counts = split_tiers(shipment_cnt)
    variable = sum(cnt * price for cnt, (_l, _u, price) in zip(counts, TIERS))
    return FIXED_FEE + variable, counts


# ---------------------------------------------------------------------------
# master からの課金対象判定
# ---------------------------------------------------------------------------


@dataclass
class MasterRow:
    code: str
    nickname: str
    channels: list[str]
    shop_active: list[bool]
    account_active: bool
    agreed_on: dt.date | None
    bill_start: dt.date | None
    bill_end: dt.date | None
    raw: dict[str, str]

    @property
    def active_channels(self) -> list[str]:
        pairs = zip(self.channels, self.shop_active + [False] * len(self.channels))
        return [ch for ch, active in pairs if active]


def load_master(path: str) -> list[MasterRow]:
    rows = read_table(path)
    out = []
    for r in rows:
        code = r.get("code", "").strip()
        if not code:
            continue
        channels = [c.lower() for c in split_list(r.get("連携先EC", ""))]
        active = [v.lower() == "true" for v in split_list(r.get("ショップ有効", ""))]
        out.append(
            MasterRow(
                code=code,
                nickname=r.get("nickname", ""),
                channels=channels,
                shop_active=active,
                account_active=to_int(r.get("アカウント有効", "")) == 1,
                agreed_on=parse_date(r.get("規約合意日", "")),
                bill_start=parse_date(r.get("請求開始日", "")),
                bill_end=parse_date(r.get("請求終了日", "")),
                raw=r,
            )
        )
    return out


def judge_multichannel(row: MasterRow) -> tuple[str, str]:
    """マルチチャネル課金対象かを判定する。

    戻り値は (判定, 理由)。判定は BILLABLE / NOT_BILLABLE / UNDETERMINABLE。
    UNDETERMINABLE は BASE の新アーキ／旧アーキが master からは判別できず、
    その判別によって結論が変わる場合に返す。
    """
    active = row.active_channels
    billable = [c for c in active if c in BILLABLE_CHANNELS]
    unknown = [c for c in active if c in UNDETERMINABLE_CHANNELS]
    unclassified = [
        c for c in active
        if c not in BILLABLE_CHANNELS
        and c not in NON_BILLABLE_CHANNELS
        and c not in UNDETERMINABLE_CHANNELS
    ]

    reason = f"有効ショップ {len(active)}件 / 課金カウント対象 {len(billable)}件"
    if unclassified:
        return "UNDETERMINABLE", f"{reason} / 未分類チャネル {sorted(set(unclassified))} あり"
    if len(billable) >= 2:
        return "BILLABLE", reason
    if unknown and len(billable) + len(unknown) >= 2:
        return "UNDETERMINABLE", f"{reason} / BASE {len(unknown)}件の新旧アーキ判別が必要"
    return "NOT_BILLABLE", reason


def expected_billed(master: list[MasterRow], start: dt.date, end: dt.date) -> tuple[set[str], dict[str, MasterRow]]:
    """対象月に請求されるべき acc の集合を、請求開始日／終了日から求める。"""
    by_code = {m.code: m for m in master}
    expected = set()
    for m in master:
        if m.bill_start is None:
            continue
        if m.bill_start > end:
            continue
        if m.bill_end is not None and m.bill_end < start:
            continue
        expected.add(m.code)
    return expected, by_code


# ---------------------------------------------------------------------------
# 各チェック
# ---------------------------------------------------------------------------


def check_master_registration(rep: Report, master: list[MasterRow], start: dt.date, end: dt.date) -> None:
    """請求開始日の登録漏れ・登録内容の矛盾を見る（請求漏れの主因）。"""
    candidates: list[MasterRow] = []
    undeterminable: list[str] = []
    for m in master:
        verdict, reason = judge_multichannel(m)

        # 合意済みなのに請求開始日がない = 請求漏れ予備軍
        if m.agreed_on is not None and m.bill_start is None:
            sev = "BLOCKER" if m.agreed_on <= end else "WARN"
            rep.add(
                sev,
                "master.請求開始日未登録",
                m.code,
                f"規約合意日 {m.agreed_on} が登録済みだが請求開始日が空。請求漏れになる",
                nickname=m.nickname,
                agreed_on=str(m.agreed_on),
                multichannel=verdict,
            )

        # 課金対象の条件を満たすが合意日がない = 未合意の課金候補。
        # 営業がこれから合意を取る通常の状態でもあるため INFO に留め、件数だけ集計する。
        if verdict == "BILLABLE" and m.account_active and m.agreed_on is None and m.bill_start is None:
            candidates.append(m)
            rep.info(
                "master.課金候補（未合意）",
                m.code,
                f"マルチチャネル課金条件を満たすが規約合意日が空（{reason}）",
                nickname=m.nickname,
                active_channels=m.active_channels,
            )

        if m.bill_start is None:
            continue

        # 請求開始日は月初1日であるべき
        if m.bill_start.day != 1:
            rep.warn(
                "master.請求開始日が月初でない",
                m.code,
                f"請求開始日 {m.bill_start} が1日ではない。日割りは行わない運用のため月初に揃える",
                nickname=m.nickname,
            )

        # 請求終了日は月末であるべき
        if m.bill_end is not None:
            last = calendar.monthrange(m.bill_end.year, m.bill_end.month)[1]
            if m.bill_end.day != last:
                rep.warn(
                    "master.請求終了日が月末でない",
                    m.code,
                    f"請求終了日 {m.bill_end} が月末ではない",
                    nickname=m.nickname,
                )
            if m.bill_end < m.bill_start:
                rep.blocker(
                    "master.請求期間が逆転",
                    m.code,
                    f"請求終了日 {m.bill_end} が請求開始日 {m.bill_start} より前",
                    nickname=m.nickname,
                )
            else:
                months = (m.bill_end.year - m.bill_start.year) * 12 + (m.bill_end.month - m.bill_start.month) + 1
                if months < 3:
                    rep.warn(
                        "master.最低利用期間3ヶ月未満",
                        m.code,
                        f"請求期間が {months}ヶ月（{m.bill_start}〜{m.bill_end}）。最低3ヶ月の規約と矛盾する",
                        nickname=m.nickname,
                    )

        # 請求中なのにアカウントが無効
        in_term = m.bill_start <= end and (m.bill_end is None or m.bill_end >= start)
        if in_term and not m.account_active:
            rep.warn(
                "master.無効アカウントが請求対象",
                m.code,
                "請求期間内だがアカウント有効フラグが 0。請求してよいか確認が必要",
                nickname=m.nickname,
            )

        # 請求中なのに課金条件を満たさなくなっている = 過剰請求の疑い
        if in_term and verdict == "NOT_BILLABLE":
            rep.warn(
                "master.課金条件を満たさない請求対象",
                m.code,
                f"請求期間内だがマルチチャネル条件を満たさない（{reason}）。解約漏れ／請求終了日の登録漏れの可能性",
                nickname=m.nickname,
                active_channels=m.active_channels,
            )
        if in_term and verdict == "UNDETERMINABLE":
            undeterminable.append(m.code)
            rep.warn(
                "master.課金条件が判別不能",
                m.code,
                f"BASE の新旧アーキ等により自動判定できない（{reason}）。Admin で (Fraise) 表記を目視確認",
                nickname=m.nickname,
                active_channels=m.active_channels,
            )

    rep.stats["billing_candidate_count"] = len(candidates)
    rep.stats["undeterminable_count"] = len(undeterminable)


def check_coverage(
    rep: Report,
    csv_rows: list[dict[str, str]],
    master: list[MasterRow],
    start: dt.date,
    end: dt.date,
) -> None:
    """期待される請求対象と CSV の突合（請求漏れ・過剰請求）。"""
    expected, by_code = expected_billed(master, start, end)
    actual = [r.get("acc", "").strip() for r in csv_rows]
    actual_set = {a for a in actual if a}

    for code in sorted(expected - actual_set):
        m = by_code[code]
        rep.blocker(
            "coverage.請求漏れ",
            code,
            f"請求期間内（{m.bill_start}〜{m.bill_end or '継続中'}）だが調整額CSVに行がない",
            nickname=m.nickname,
        )

    for code in sorted(actual_set - expected):
        m = by_code.get(code)
        if m is None:
            rep.blocker(
                "coverage.master不在",
                code,
                "調整額CSVにあるが master に存在しない。荷主コードの誤りの可能性",
            )
        else:
            rep.blocker(
                "coverage.過剰請求",
                code,
                f"請求期間外（開始 {m.bill_start or '未登録'} / 終了 {m.bill_end or '継続中'}）なのに調整額CSVに行がある",
                nickname=m.nickname,
            )

    dupes = {a for a in actual_set if actual.count(a) > 1}
    for code in sorted(dupes):
        rep.blocker(
            "coverage.CSV内重複",
            code,
            f"調整額CSV内に同一 acc が {actual.count(code)} 行ある。二重請求になる",
        )

    rep.stats["expected_count"] = len(expected)
    rep.stats["csv_row_count"] = len(csv_rows)


def check_amounts(
    rep: Report,
    csv_rows: list[dict[str, str]],
    target_rows: list[dict[str, str]],
    term: str,
    end: dt.date,
) -> None:
    """金額の独立再計算と、target_data / memo / amount の三者突合。"""
    target_by_acc: dict[str, dict[str, str]] = {}
    for r in target_rows:
        acc = r.get("acc", "").strip()
        if not acc:
            continue
        if acc in target_by_acc:
            rep.blocker("target.重複行", acc, "target_data に同一 acc が複数行ある")
        target_by_acc[acc] = r

    total = 0
    for row in csv_rows:
        acc = row.get("acc", "").strip()
        if not acc:
            rep.blocker("csv.acc空", "", "acc が空の行がある", row=row)
            continue

        amount = to_int(row.get("amount", ""))
        if amount is None:
            rep.blocker("csv.amount不正", acc, f"amount が数値として読めない: {row.get('amount')!r}")
            continue
        total += amount

        if amount < FIXED_FEE:
            rep.blocker(
                "amount.基本料未満",
                acc,
                f"amount {amount:,}円 が基本利用料 {FIXED_FEE:,}円 を下回っている",
            )

        target = target_by_acc.get(acc)
        if target is None:
            rep.blocker(
                "amount.元データ不在",
                acc,
                "調整額CSVに行があるが target_data に対応行がない。金額の根拠を確認できない",
            )
            continue

        shipment = to_int(target.get("shipment_cnt", ""))
        if shipment is None:
            rep.blocker("target.件数不正", acc, f"shipment_cnt が読めない: {target.get('shipment_cnt')!r}")
            continue

        expected_amount, expected_counts = calc_amount(shipment)

        if amount != expected_amount:
            rep.blocker(
                "amount.再計算不一致",
                acc,
                f"出荷 {shipment:,}件 からの再計算 {expected_amount:,}円 に対し CSV は {amount:,}円（差 {amount - expected_amount:+,}円）",
                shipment_cnt=shipment,
                expected=expected_amount,
                actual=amount,
            )

        # target_data の段別件数そのものが正しいか
        sheet_counts = [to_int(target.get(col, "")) for col in TIER_COLUMNS]
        if None in sheet_counts:
            rep.blocker("target.段別件数不正", acc, "target_data の段別件数に数値でない値がある")
        else:
            if sum(sheet_counts) != shipment:
                rep.blocker(
                    "target.段別件数の合計不一致",
                    acc,
                    f"段別件数の合計 {sum(sheet_counts):,} が shipment_cnt {shipment:,} と一致しない",
                )
            if sheet_counts != expected_counts:
                rep.blocker(
                    "target.段配分の誤り",
                    acc,
                    f"段別件数 {sheet_counts} が階段式の配分 {expected_counts} と一致しない",
                )

        fixed = to_int(target.get("fixed_fee", ""))
        if fixed is not None and fixed != FIXED_FEE:
            rep.warn("target.基本料が既定と異なる", acc, f"fixed_fee が {fixed:,}円（既定 {FIXED_FEE:,}円）")

        # memo の内訳が amount と整合しているか
        check_memo(rep, acc, row.get("memo", ""), shipment, amount, expected_counts)

        # 倉庫コードの整合
        wb_csv = row.get("warehouseBaseCode", "").strip()
        wb_target = target.get("wb", "").strip()
        if not wb_csv:
            rep.blocker("csv.倉庫コード空", acc, "warehouseBaseCode が空")
        elif wb_target and wb_csv != wb_target:
            rep.blocker(
                "csv.倉庫コード不一致",
                acc,
                f"CSV の倉庫コード {wb_csv} が target_data の {wb_target} と一致しない",
            )

        # 対象日は対象月の末日で全行そろっているべき
        target_date = parse_date(row.get("targetDate", ""))
        if target_date is None:
            rep.blocker("csv.調整日付不正", acc, f"targetDate が読めない: {row.get('targetDate')!r}")
        elif target_date != end:
            rep.blocker(
                "csv.調整日付が対象月末でない",
                acc,
                f"targetDate {target_date} が対象月 {term} の末日 {end} ではない",
            )

        td_target = parse_date(target.get("target_date", ""))
        if td_target is not None and td_target != end:
            rep.blocker(
                "target.対象日が対象月末でない",
                acc,
                f"target_data の target_date {td_target} が {end} ではない。BigQuery の抽出月がずれている可能性",
            )
        if target.get("target_term", "").strip() not in ("", term):
            rep.blocker(
                "target.対象月不一致",
                acc,
                f"target_data の target_term {target.get('target_term')} が指定した対象月 {term} と異なる",
            )

    csv_accs = {r.get("acc", "").strip() for r in csv_rows if r.get("acc", "").strip()}
    for acc in sorted(set(target_by_acc) - csv_accs):
        rep.blocker(
            "amount.CSV生成漏れ",
            acc,
            "target_data に請求対象として出ているが調整額CSVに行がない。CSV生成が途中で切れた可能性",
        )

    rep.stats["total_amount"] = total
    rep.stats["target_row_count"] = len(target_by_acc)


def check_memo(
    rep: Report,
    acc: str,
    memo: str,
    shipment: int,
    amount: int,
    expected_counts: list[int],
) -> None:
    """調整理由（memo）の本文が金額・件数と食い違っていないかを見る。

    memo は請求書に載り荷主の目に触れるため、amount と一致していることが重要。
    """
    if not memo:
        rep.blocker("memo.空", acc, "調整理由が空。請求書に理由が出ない")
        return
    if MEMO_TITLE not in memo:
        rep.warn("memo.表題不一致", acc, f"調整理由に「{MEMO_TITLE}」が含まれていない")

    normalized = memo.replace(",", "")

    m = re.search(r"【件数】\s*([0-9]+)件", normalized)
    if m is None:
        rep.warn("memo.件数を読み取れない", acc, "調整理由から【件数】を抽出できない")
    elif int(m.group(1)) != shipment:
        rep.blocker(
            "memo.件数不一致",
            acc,
            f"調整理由の件数 {int(m.group(1)):,} が target_data の {shipment:,} と一致しない",
        )

    m = re.search(r"【合計料金】\s*([0-9]+)円", normalized)
    if m is None:
        rep.warn("memo.合計を読み取れない", acc, "調整理由から【合計料金】を抽出できない")
    elif int(m.group(1)) != amount:
        rep.blocker(
            "memo.合計不一致",
            acc,
            f"調整理由の合計 {int(m.group(1)):,}円 が amount {amount:,}円 と一致しない",
        )

    # 各段の「N件 × P円 = S円」がすべて成立しているか
    breakdown = re.findall(r"([0-9]+)件\s*×\s*([0-9]+)円\s*=\s*([0-9]+)円", normalized)
    if len(breakdown) != len(TIERS):
        rep.warn(
            "memo.内訳の段数が合わない",
            acc,
            f"内訳の行数が {len(breakdown)}（期待 {len(TIERS)}）",
        )
    subtotal = 0
    for idx, (cnt_s, price_s, sub_s) in enumerate(breakdown):
        cnt, price, sub = int(cnt_s), int(price_s), int(sub_s)
        if cnt * price != sub:
            rep.blocker("memo.内訳の掛け算が誤り", acc, f"{cnt:,}件 × {price}円 = {sub:,}円 になっていない")
        subtotal += sub
        if idx < len(TIERS):
            if price != TIERS[idx][2]:
                rep.blocker(
                    "memo.単価が料金表と異なる",
                    acc,
                    f"{idx + 1}段目の単価 {price}円 が料金表の {TIERS[idx][2]}円 と異なる",
                )
            if cnt != expected_counts[idx]:
                rep.blocker(
                    "memo.段別件数不一致",
                    acc,
                    f"{idx + 1}段目の件数 {cnt:,} が再計算の {expected_counts[idx]:,} と異なる",
                )
    if breakdown and subtotal + FIXED_FEE != amount:
        rep.blocker(
            "memo.内訳合計不一致",
            acc,
            f"内訳の従量計 {subtotal:,}円 + 基本料 {FIXED_FEE:,}円 が amount {amount:,}円 と一致しない",
        )


def check_csv_format(rep: Report, csv_rows: list[dict[str, str]], header: list[str]) -> None:
    """Admin の一括登録が通る形になっているか。"""
    missing = [c for c in CSV_COLUMNS if c not in header]
    if missing:
        rep.blocker("format.列不足", "", f"必須列が足りない: {missing}", header=header)
    extra = [c for c in header if c and c not in CSV_COLUMNS]
    if extra:
        rep.warn("format.余分な列", "", f"テンプレートにない列がある: {extra}")
    if header[: len(CSV_COLUMNS)] != CSV_COLUMNS and not missing:
        rep.warn("format.列順が異なる", "", f"列順がテンプレートと異なる: {header}")

    for row in csv_rows:
        acc = row.get("acc", "").strip()
        for col, expected in FIXED_CSV_VALUES.items():
            actual = row.get(col, "").strip()
            if actual != expected:
                rep.blocker(
                    "format.固定値の誤り",
                    acc,
                    f"{col} は {expected} であるべきだが {actual!r} になっている",
                )
        if row.get("taxExemptAmount", "").strip():
            rep.warn(
                "format.免税額が入っている",
                acc,
                "taxExemptAmount は明細区分が関税のときのみ有効。値が入っている",
            )
        for col in ("acc", "amount"):
            if not row.get(col, "").strip():
                rep.blocker("format.必須項目が空", acc, f"{col} が空")


def check_month_over_month(
    rep: Report,
    csv_rows: list[dict[str, str]],
    prev_rows: list[dict[str, str]],
    master: list[MasterRow],
) -> dict[str, Any]:
    """前月の調整額CSVと比較し、増減と出入りを出す。"""
    by_code = {m.code: m for m in master}
    cur = {r["acc"].strip(): to_int(r.get("amount", "")) or 0 for r in csv_rows if r.get("acc", "").strip()}
    prev = {r["acc"].strip(): to_int(r.get("amount", "")) or 0 for r in prev_rows if r.get("acc", "").strip()}

    added = sorted(set(cur) - set(prev))
    removed = sorted(set(prev) - set(cur))

    for code in removed:
        m = by_code.get(code)
        if m is None or m.bill_end is None:
            rep.blocker(
                "mom.前月あり今月なし",
                code,
                f"前月は {prev[code]:,}円 請求していたが今月は対象外。請求終了日が登録されていない",
                prev_amount=prev[code],
            )
        else:
            rep.info(
                "mom.請求終了",
                code,
                f"請求終了日 {m.bill_end} により今月から対象外（前月 {prev[code]:,}円）",
            )

    for code in added:
        m = by_code.get(code)
        rep.info(
            "mom.新規請求",
            code,
            f"今月から請求開始（{cur[code]:,}円 / 請求開始日 {m.bill_start if m else '不明'}）",
            nickname=m.nickname if m else "",
        )

    for code in sorted(set(cur) & set(prev)):
        delta = cur[code] - prev[code]
        if prev[code] > 0 and abs(delta) >= MOM_AMOUNT_ABS and cur[code] / prev[code] >= MOM_AMOUNT_RATIO:
            rep.warn(
                "mom.金額の急増",
                code,
                f"前月 {prev[code]:,}円 → 今月 {cur[code]:,}円（{delta:+,}円）。出荷件数の急増か抽出条件の誤りかを確認",
            )
        elif prev[code] > 0 and cur[code] < prev[code] and abs(delta) >= MOM_AMOUNT_ABS:
            rep.warn(
                "mom.金額の急減",
                code,
                f"前月 {prev[code]:,}円 → 今月 {cur[code]:,}円（{delta:+,}円）",
            )

    summary = {
        "prev_company_count": len(prev),
        "cur_company_count": len(cur),
        "prev_total": sum(prev.values()),
        "cur_total": sum(cur.values()),
        "added": added,
        "removed": removed,
    }
    summary["company_delta"] = summary["cur_company_count"] - summary["prev_company_count"]
    summary["total_delta"] = summary["cur_total"] - summary["prev_total"]
    return summary


def check_post_registration(
    rep: Report,
    csv_rows: list[dict[str, str]],
    bill_rows: list[dict[str, str]],
    end: dt.date,
) -> None:
    """投入後、Admin に登録された調整額と CSV を突合する。"""
    expected = {}
    for r in csv_rows:
        acc = r.get("acc", "").strip()
        if acc:
            expected[acc] = to_int(r.get("amount", "")) or 0

    registered: dict[str, list[int]] = {}
    for r in bill_rows:
        code = r.get("code", "").strip()
        target_date = parse_date(r.get("target_date", ""))
        if not code or target_date != end:
            continue
        registered.setdefault(code, []).append(to_int(r.get("amount", "")) or 0)

    for acc, amount in sorted(expected.items()):
        got = registered.get(acc)
        if got is None:
            rep.blocker(
                "post.登録されていない",
                acc,
                f"CSV では {amount:,}円 を登録するはずだが、対象日 {end} の調整額が見つからない",
            )
            continue
        if len(got) > 1:
            rep.blocker(
                "post.二重登録",
                acc,
                f"対象日 {end} の調整額が {len(got)}件 登録されている（{got}）。CSVを重複投入した可能性",
            )
        if got[0] != amount:
            rep.blocker(
                "post.金額不一致",
                acc,
                f"登録額 {got[0]:,}円 が CSV の {amount:,}円 と一致しない（差 {got[0] - amount:+,}円）",
            )

    for acc in sorted(set(registered) - set(expected)):
        rep.blocker(
            "post.CSVにない登録",
            acc,
            f"対象日 {end} に調整額 {registered[acc]} が登録されているが、投入した CSV には含まれていない",
        )

    rep.stats["post_registered_count"] = len(registered)
    rep.stats["post_registered_total"] = sum(v[0] for v in registered.values() if v)


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"BLOCKER": 0, "WARN": 1, "INFO": 2}


def render_text(rep: Report) -> str:
    d = rep.to_dict()
    out = [
        f"OMS課金 調整額チェック  対象月 {rep.term}",
        "=" * 72,
        f"判定: {d['summary']['verdict']}   BLOCKER {d['summary']['blocker']} / WARN {d['summary']['warn']} / INFO {d['summary']['info']}",
        "",
    ]
    stats = d["stats"]
    if stats:
        out.append("[集計]")
        if "csv_row_count" in stats:
            out.append(f"  請求社数（CSV行数）      : {stats['csv_row_count']}社")
        if "expected_count" in stats:
            out.append(f"  master からの期待社数    : {stats['expected_count']}社")
        if "target_row_count" in stats:
            out.append(f"  target_data 行数         : {stats['target_row_count']}社")
        if "total_amount" in stats:
            out.append(f"  請求総額（税抜）         : {stats['total_amount']:,}円")
        if "billing_candidate_count" in stats:
            out.append(f"  課金候補（未合意）       : {stats['billing_candidate_count']}社")
        if stats.get("undeterminable_count"):
            out.append(f"  課金条件が判別不能       : {stats['undeterminable_count']}社（目視確認が必要）")
        mom = stats.get("mom")
        if mom:
            out.append(
                f"  前月比 社数              : {mom['prev_company_count']}社 → {mom['cur_company_count']}社（{mom['company_delta']:+d}社）"
            )
            out.append(
                f"  前月比 総額              : {mom['prev_total']:,}円 → {mom['cur_total']:,}円（{mom['total_delta']:+,}円）"
            )
        if "post_registered_count" in stats:
            out.append(f"  登録済み件数             : {stats['post_registered_count']}件")
            out.append(f"  登録済み総額             : {stats['post_registered_total']:,}円")
        out.append("")

    findings = sorted(rep.findings, key=lambda f: (SEVERITY_ORDER[f.severity], f.check, f.acc))
    if not findings:
        out.append("指摘なし。")
        return "\n".join(out)

    current = None
    for f in findings:
        if f.severity != current:
            current = f.severity
            out.append(f"[{current}]")
        acc = f.acc or "-"
        out.append(f"  {acc:<8} {f.check}")
        out.append(f"           {f.message}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OMS課金 調整額CSVの検証")
    ap.add_argument("--term", required=True, help="対象月 YYYY-MM（請求対象となる出荷実績の月）")
    ap.add_argument("--master", required=True, help="master シートの CSV/TSV")
    ap.add_argument("--target-data", required=True, help="Target_data シートの CSV/TSV")
    ap.add_argument("--create-csv", required=True, help="create_csv シート（投入する調整額CSV）")
    ap.add_argument("--prev-create-csv", help="前月の調整額CSV（前月比較に使う）")
    ap.add_argument("--bill-adjustments", help="bill_adjustments シート（投入後チェックに使う）")
    ap.add_argument("--json", help="検証結果 JSON の出力先")
    args = ap.parse_args(argv)

    if not re.fullmatch(r"\d{4}-\d{2}", args.term):
        print(f"--term は YYYY-MM 形式で指定する: {args.term!r}", file=sys.stderr)
        return 2

    start, end = term_bounds(args.term)
    rep = Report(args.term)

    master = load_master(args.master)
    target_rows = read_table(args.target_data)
    csv_rows = read_create_csv(args.create_csv)
    header = list(csv_rows[0].keys()) if csv_rows else []

    if not csv_rows:
        rep.blocker("input.CSVが空", "", "調整額CSVに1行もない。生成が失敗している可能性")

    check_csv_format(rep, csv_rows, header)
    check_master_registration(rep, master, start, end)
    check_coverage(rep, csv_rows, master, start, end)
    check_amounts(rep, csv_rows, target_rows, args.term, end)

    if args.prev_create_csv:
        prev_rows = read_create_csv(args.prev_create_csv)
        rep.stats["mom"] = check_month_over_month(rep, csv_rows, prev_rows, master)

    if args.bill_adjustments:
        bill_rows = read_table(args.bill_adjustments)
        check_post_registration(rep, csv_rows, bill_rows, end)

    print(render_text(rep))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(rep.to_dict(), fh, ensure_ascii=False, indent=2)
        print(f"\nJSON: {args.json}")

    return 1 if rep.count("BLOCKER") else 0


if __name__ == "__main__":
    raise SystemExit(main())
