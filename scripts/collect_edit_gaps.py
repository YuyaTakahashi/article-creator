#!/usr/bin/env python3
"""公開済み記事について「AIの初稿」と「人が直した公開版」の差分を集める。

記事の質を上げる手がかりは、人がどこを直したかに一番はっきり出る。
初稿と公開版を段落単位で突き合わせ、差分を logs/gaps/ に残す。
残した差分は pipeline/learn-from-edits-prompt.md が読み、執筆ルールの改訂案に変える。

初稿の出どころ:
  1. drafts/_baseline/{用語}_{版}.md … Doc化のときに取ったスナップショット（確実）
  2. drafts/{用語}.md              … 1が無いとき。article-review はDoc化の前に走るので、
                                     Doc化以降に触っていなければこれが初稿にあたる

使い方:
    python3 scripts/collect_edit_gaps.py              # 未確認の公開済み記事をすべて
    python3 scripts/collect_edit_gaps.py --term 黄金比 # 1件だけ
    python3 scripts/collect_edit_gaps.py --recheck    # 確認済みの記事も取り直す
    python3 scripts/collect_edit_gaps.py --dry-run    # 用語DBに確認日を書かない
"""

import argparse
import base64
import difflib
import html as html_mod
import json
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
GAP_CHECKED_COL = "W"          # GAP確認日。空なら未確認
SPLIT = "-- wp分割ライン--"

RUBY_MD = re.compile(r"([A-Za-z0-9.\-]+)¥[^¥]+¥")      # 英字¥カナ¥ → 英字
RUBY_HTML = re.compile(r"<ruby>(.*?)<rt>.*?</rt></ruby>", re.S)
FIGURE = re.compile(r"<figure.*?</figure>", re.S)
TAG = re.compile(r"<[^>]+>")
BLOCK_END = re.compile(r"</(p|h[1-6]|li|blockquote|tr|div)>", re.I)


def short(path):
    """リポジトリ内なら相対パス、外なら絶対パスで見せる。"""
    try:
        return str(Path(path).relative_to(BASE))
    except ValueError:
        return str(path)


def load_env():
    env = {}
    p = BASE / ".env"
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def normalize(text):
    """比較できる形にそろえる。全角半角・連続空白・記号の揺れで差分が出ないようにする。"""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def md_paragraphs(md_text):
    """初稿MDを段落のリストにする。分割ラインより後ろが本文。"""
    body = md_text.split(SPLIT, 1)[1] if SPLIT in md_text else md_text
    body = FIGURE.sub("", body)
    body = RUBY_MD.sub(r"\1", body)
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)     # リンクは表示文字だけ
    body = re.sub(r"\*\*([^*]+)\*\*", r"\1", body)
    body = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", body)
    body = TAG.sub("", body)

    paras = []
    for block in re.split(r"\n\s*\n", body):
        for line in block.split("\n"):
            line = re.sub(r"^\s*(#{1,6}|[-*>]|\d+\.)\s*", "", line)   # 見出し・箇条書き・引用の印
            line = re.sub(r"^\s*\|", "", line).replace("|", " ")       # 表は行を1段落として扱う
            line = normalize(line)
            if len(line) >= 8 and not re.fullmatch(r"[-\s]+", line):
                paras.append(line)
    return paras


def html_paragraphs(html_text):
    """WP公開版のHTMLを段落のリストにする。"""
    text = FIGURE.sub("", html_text)
    text = RUBY_HTML.sub(r"\1", text)
    text = BLOCK_END.sub("\n\n", text)
    text = TAG.sub("", text)
    text = html_mod.unescape(text)
    paras = []
    for line in re.split(r"\n+", text):
        line = normalize(line)
        if len(line) >= 8:
            paras.append(line)
    return paras


def fetch_wp(env, post_id):
    site = env["WP_SITE_URL"].rstrip("/")
    post_type = env.get("WP_POST_TYPE", "posts")
    auth = base64.b64encode(
        f"{env['WP_USER']}:{env['WP_APP_PASS'].replace(' ', '')}".encode()).decode()
    req = urllib.request.Request(f"{site}/wp-json/wp/v2/{post_type}/{post_id}",
                                 headers={"Authorization": "Basic " + auth})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return d["content"]["rendered"], d["link"], d.get("modified", "")[:10]


def read_sheet():
    out = subprocess.run(
        ["gws", "sheets", "+read", "--spreadsheet", SHEET_ID,
         "--range", f"'{TAB}'!A1:W1000", "--format", "json"],
        capture_output=True, text=True)
    body = out.stdout[out.stdout.find("{"):] if "{" in out.stdout else ""
    if not body:
        sys.exit(f"用語DBを読めなかった: {out.stderr.strip()[:200]}")
    return json.loads(body).get("values", [])


def mark_checked(row_no, value):
    subprocess.run(
        ["gws", "sheets", "spreadsheets", "values", "update",
         "--params", json.dumps({"spreadsheetId": SHEET_ID,
                                 "range": f"{TAB}!{GAP_CHECKED_COL}{row_no}",
                                 "valueInputOption": "RAW"}),
         "--json", json.dumps({"values": [[value]]})],
        capture_output=True, text=True)


def find_baseline(term):
    hits = sorted((BASE / "drafts" / "_baseline").glob(f"{term}_*.md"))
    if hits:
        return hits[-1], "baseline"
    p = BASE / "drafts" / f"{term}.md"
    return (p, "drafts") if p.exists() else (None, None)


def build_report(gid, term, version, src_label, src_path, wp_link, wp_modified, before, after):
    sm = difflib.SequenceMatcher(None, before, after, autojunk=False)
    changed = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        changed.append((tag, before[i1:i2], after[j1:j2]))

    lines = [
        f"# {term}（{gid}）",
        "",
        f"- 生成バージョン: {version or '記録なし'}",
        f"- 初稿: `{short(src_path)}`（{src_label}）",
        f"- 公開版: {wp_link}（最終更新 {wp_modified}）",
        f"- 段落数: 初稿 {len(before)} → 公開 {len(after)}",
        f"- 手が入った箇所: {len(changed)}",
        "",
    ]
    if not changed:
        lines.append("人の手はほぼ入っていない（段落単位では一致）。")
        return "\n".join(lines) + "\n", 0

    lines.append("## 手が入った箇所")
    lines.append("")
    for n, (tag, b, a) in enumerate(changed, 1):
        label = {"replace": "書き換え", "delete": "削除", "insert": "追記"}[tag]
        lines.append(f"### {n}. {label}")
        lines.append("")
        if b:
            lines.append("**初稿**")
            lines += [f"> {x}" for x in b]
            lines.append("")
        if a:
            lines.append("**公開版**")
            lines += [f"> {x}" for x in a]
            lines.append("")
        # 1対1の書き換えは、文字単位でどこが動いたかまで出す
        if tag == "replace" and len(b) == 1 and len(a) == 1:
            inline = []
            for t, i1, i2, j1, j2 in difflib.SequenceMatcher(None, b[0], a[0]).get_opcodes():
                if t == "delete":
                    inline.append(f"[削除: {b[0][i1:i2]}]")
                elif t == "insert":
                    inline.append(f"[追加: {a[0][j1:j2]}]")
                elif t == "replace":
                    inline.append(f"[{b[0][i1:i2]} → {a[0][j1:j2]}]")
            if inline:
                lines.append("**文字単位**")
                lines.append("")
                lines.append(" ".join(inline)[:1200])
                lines.append("")
    return "\n".join(lines) + "\n", len(changed)


def main():
    ap = argparse.ArgumentParser(description="初稿と公開版の差分を集める")
    ap.add_argument("--term", help="1件だけ処理する")
    ap.add_argument("--recheck", action="store_true", help="確認済みの記事も取り直す")
    ap.add_argument("--dry-run", action="store_true", help="用語DBに確認日を書かない")
    ap.add_argument("--out-dir", help="出力先（既定は logs/gaps/{今日}）")
    args = ap.parse_args()

    env = load_env()
    rows = read_sheet()
    today = date.today().isoformat()
    out_dir = Path(args.out_dir) if args.out_dir else BASE / "logs" / "gaps" / today
    out_dir.mkdir(parents=True, exist_ok=True)

    def g(r, k):
        return str(r[k]).strip() if len(r) > k else ""

    targets = []
    for i, r in enumerate(rows[1:], start=2):
        if g(r, 7) != "公開済み" or not g(r, 16):
            continue
        if args.term and g(r, 1) != args.term:
            continue
        if g(r, 22) and not args.recheck:      # W列に確認日がある
            continue
        targets.append((i, r))

    if not targets:
        print("差分を取る対象は無し（未確認の公開済み記事なし）")
        return 0

    print(f"対象 {len(targets)} 件 → {short(out_dir)}")
    total_changed = 0
    for row_no, r in targets:
        gid, term, wp_id, version = g(r, 0), g(r, 1), g(r, 16), g(r, 18)
        src_path, src_label = find_baseline(term)
        if not src_path:
            print(f"  {gid} {term}: 初稿が見つからない（drafts/{term}.md が無い）→ 飛ばす")
            continue
        try:
            html_text, wp_link, wp_modified = fetch_wp(env, wp_id)
        except Exception as e:
            print(f"  {gid} {term}: WPから取れなかった（{e}）→ 飛ばす")
            continue

        before = md_paragraphs(src_path.read_text(encoding="utf-8"))
        after = html_paragraphs(html_text)
        report, n_changed = build_report(gid, term, version, src_label, src_path,
                                         wp_link, wp_modified, before, after)
        (out_dir / f"{term}.md").write_text(report, encoding="utf-8")
        total_changed += n_changed
        print(f"  {gid} {term}: 段落 {len(before)}→{len(after)} / 手が入った箇所 {n_changed}")
        if not args.dry_run:
            mark_checked(row_no, today)

    print(f"\n合計 {total_changed} 箇所。出力: {short(out_dir)}")
    if args.dry_run:
        print("（--dry-run のため用語DBのW列は更新していない）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
