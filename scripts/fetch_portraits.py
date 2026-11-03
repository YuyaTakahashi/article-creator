#!/usr/bin/env python3
"""下書きMDの `## 語源・提唱者` に出てくる人物の肖像を、Wikipedia から取って <figure> で差し込む。

肖像を入れる指示は CLAUDE.md の F5 にしか無く、執筆プロンプト・生成バッチ・GPTでの作り直しの
どれにも工程として無かった。そのため 2026-10 以降の記事は肖像がほとんど空になっていた。
ここで工程にし、register_draft.py（用語DBへの書き戻し）と regenerate_gpt.py（作り直し）から呼ぶ。

- 対象は `## 語源…` の節に、ルビ記法（`Christine¥クリスティーン¥ Peterson¥ピーターソン¥`）で書かれた人物。
  1つの節に何人いてもよく、見つかった人数ぶん入れる
- 取り違えを防ぐため、次をすべて満たすときだけ入れる
    1. 英語版 Wikipedia にその名前の記事があり（転送は辿る）、曖昧さ回避ページではない
    2. その記事の Wikidata 項目が「人間（Q5）」である
    3. 記事の代表画像が Wikimedia Commons の画像である（英語版だけにある非自由画像は使わない）
- すでに同じ人物（alt が同じカタカナ名）の <figure> があれば何もしない
- 作り直し（--old に前の版を渡す）では、前の版にあった肖像を先に引き継ぐ。
  手で入れた肖像（Wikipedia 以外の画像など）を、書き直しで失わないため
- 差し込む位置は、その人物が最初に出てくる段落の直後

使い方:
    python3 scripts/fetch_portraits.py "drafts/オープンソース.md"
    python3 scripts/fetch_portraits.py "drafts/オープンソース.md" --old drafts/_baseline/オープンソース_v16.md
    python3 scripts/fetch_portraits.py "drafts/オープンソース.md" --dry-run   書き込まずに結果だけ見る
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portraits import FIGURE_RE, ALT_RE, RUBY_RE  # noqa: E402

UA = "article-creator-portraits/1.0 (https://uxdaystokyo.com/; UX glossary portrait lookup) python-urllib"
WIKI_API = "https://en.wikipedia.org/w/api.php"
WD_API = "https://www.wikidata.org/w/api.php"
# ルビ付きの語（`Peterson¥ピーターソン¥`）。愛称は引用符で囲まれる（`“Sepp”¥ゼップ¥`）
TOKEN = r"[“\"]?[A-Za-z][A-Za-z.'’\-]*[”\"]?[¥￥][^¥￥\n]+[¥￥]"
TOKEN_RE = re.compile(r"([“\"]?)([A-Za-z][A-Za-z.'’\-]*)[”\"]?[¥￥]([^¥￥\n]+)[¥￥]")
# ルビ付きの語が空白区切りで1〜4個並んだものを1人の名前とみなす
NAME_RE = re.compile(TOKEN + r"(?:[ 　]+" + TOKEN + r"){0,3}")
FIGURE_TMPL = ('<figure style="text-align:center;margin:1.5em auto;"><img src="{src}" alt="{alt}" '
               'style="width:200px;max-width:45%;height:auto;display:block;margin:0 auto;">'
               '<figcaption style="font-size:0.85em;color:#666;">{alt}（出典：<a href="{page}" '
               'target="_blank" rel="noopener">{page}</a>）</figcaption></figure>')


def _get(url, params, tries=4):
    """Wikimedia の API は短時間に続けて呼ぶと 429 を返すので、間隔を空け、Retry-After に従って待ち直す"""
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode({**params, "maxlag": 5}),
                                 headers={"User-Agent": UA})
    for i in range(tries):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503) or i == tries - 1:
                raise
            wait = int(e.headers.get("Retry-After", "0") or 0) or 2 ** (i + 1)
            time.sleep(min(wait, 30))


def lookup(name_en):
    """英語名から (画像URL, 記事URL) を返す。条件を満たさなければ (None, 理由)。"""
    d = _get(WIKI_API, {"action": "query", "titles": name_en, "redirects": 1, "format": "json",
                        "prop": "pageimages|pageprops", "piprop": "original",
                        "ppprop": "wikibase_item|disambiguation"})
    page = next(iter(d.get("query", {}).get("pages", {}).values()), {})
    if "missing" in page or not page:
        return None, "Wikipedia に記事が無い"
    props = page.get("pageprops", {})
    if "disambiguation" in props:
        return None, "曖昧さ回避ページ"
    qid = props.get("wikibase_item")
    if not qid:
        return None, "Wikidata 項目が無い"
    claims = _get(WD_API, {"action": "wbgetclaims", "entity": qid, "property": "P31", "format": "json"})
    kinds = {c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
             for c in claims.get("claims", {}).get("P31", [])}
    if "Q5" not in kinds:
        return None, f"人物の記事ではない（{qid}）"
    # API は ?utm_source=… を付けて返すことがあるので外す（WPメディアへ複製するときのファイル名が崩れるため）
    src = page.get("original", {}).get("source", "").split("?")[0]
    if not src:
        return None, "代表画像が無い"
    if "/wikipedia/commons/" not in src:
        return None, "Commons の画像ではない（非自由画像の可能性）"
    title = page.get("title", name_en).replace(" ", "_")
    return src, "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title, safe="_()',")


def _origin_span(text):
    m = re.search(r"^## 語源[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return (m.start(1), m.end(1)) if m else None


def _paragraphs(section):
    return [p for p in re.split(r"\n\s*\n", section) if p.strip()]


def _insert_after(section, needle, html):
    """needle を含む最初の段落の直後に html を置く。同じ段落の後ろに figure が続いていれば、その後ろに足す"""
    paras = _paragraphs(section)
    for i, p in enumerate(paras):
        if needle in p and not p.strip().startswith("<figure"):
            j = i + 1
            while j < len(paras) and paras[j].strip().startswith("<figure"):
                j += 1
            paras.insert(j, html)
            return "\n\n".join(x.strip("\n") for x in paras) + "\n\n", True
    return section, False


def people(text, section):
    """語源の節で触れられている人物を、出てくる順に [(英語名の候補, カタカナ名, 節の中の目印)] で返す。

    ルビ付きのフルネームは本文のどこに書かれていてもよい（リード文で初出し、語源の節では
    「ケストラー氏」とだけ書く記事が多いため）。語源の節に、フルネーム・英字の姓・カタカナの姓の
    どれかが出てくる人物だけを対象にし、目印はその節で最初に出てくる文字列にする。
    """
    seen, out = set(), []
    for m in NAME_RE.finditer(text):
        toks = TOKEN_RE.findall(m.group(0))  # [(引用符, 英字, カナ)]
        plain = [t for t in toks if not t[0]]
        nick = [t for t in toks if t[0]]
        if not plain:
            continue
        last = plain[-1]
        cands = [" ".join(t[1] for t in plain)]
        if nick:
            cands.append(f"{nick[0][1]} {last[1]}")
        if len(plain) > 2:
            cands.append(f"{plain[0][1]} {last[1]}")
        kana = "・".join(t[2] for t in toks)
        if cands[0] in seen:
            continue
        seen.add(cands[0])
        if m.group(0) in section:
            mark = m.group(0)
        else:
            pos = [(section.find(x), x) for x in (last[2], last[1] + "¥") if section.find(x) >= 0]
            if not pos:
                continue
            mark = min(pos)[1]
        out.append((cands, kana, mark))
    return out


def lookup_any(cands):
    reason = ""
    for c in dict.fromkeys(cands):
        src, page = lookup(c)
        if src:
            return src, page
        reason = f"{c}: {page}"
    return None, reason


def ensure_portraits(text, old_text=None, fetch=True):
    """(新しい本文, 報告の行) を返す。本文が変わらなければ同じ文字列を返す"""
    span = _origin_span(text)
    if not span:
        return text, ["語源の節が無いので肖像は扱わない"]
    head, section, tail = text[:span[0]], text[span[0]:span[1]], text[span[1]:]
    have = {a for a in ALT_RE.findall(" ".join(FIGURE_RE.findall(section)))}
    report = []

    # 1. 前の版の肖像を引き継ぐ（その人物が新しい本文にもいる場合だけ）
    if old_text:
        ospan = _origin_span(old_text)
        for fig in FIGURE_RE.findall(old_text[ospan[0]:ospan[1]] if ospan else ""):
            alt = (ALT_RE.search(fig) or [None, ""])[1]
            if not alt or alt in have:
                continue
            surname = re.split(r"[・\s　]", alt)[-1]
            hit = next((mark for _, kana, mark in people(text, section) if kana.split("・")[-1] == surname), None)
            if not hit:
                report.append(f"引き継がない: {alt}（新しい本文に出てこない）")
                continue
            one = re.sub(r"\s*\n\s*", " ", fig).strip()
            section, ok = _insert_after(section, hit, one)
            if ok:
                have.add(alt)
                report.append(f"引き継いだ: {alt}")

    # 2. まだ肖像の無い人物を Wikipedia で探す
    if fetch:
        for cands, kana, mark in people(text, section):
            if kana in have or kana.split("・")[-1] in {a.split("・")[-1] for a in have}:
                continue
            try:
                src, page = lookup_any(cands)
            except Exception as e:  # ネットワーク不調で記事の工程を止めない
                report.append(f"取得失敗: {cands[0]}（{e}）")
                continue
            if not src:
                report.append(f"入れない: {kana}（{page}）")
                continue
            section, ok = _insert_after(section, mark, FIGURE_TMPL.format(src=src, alt=kana, page=page))
            if ok:
                have.add(kana)
                report.append(f"入れた: {kana}（{page}）")
    return head + section + tail, report


def main():
    ap = argparse.ArgumentParser(description="語源・提唱者の人物の肖像を Wikipedia から差し込む")
    ap.add_argument("md")
    ap.add_argument("--old", help="作り直し前の版（前の版の肖像を引き継ぐ）")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    p = Path(a.md)
    text = p.read_text(encoding="utf-8")
    old = Path(a.old).read_text(encoding="utf-8") if a.old else None
    new, report = ensure_portraits(text, old)
    for line in report:
        print("  [肖像] " + line)
    if new != text and not a.dry_run:
        p.write_text(new, encoding="utf-8")
        print(f"  [肖像] {p.name} を更新した")
    elif new == text:
        print("  [肖像] 変更なし")


if __name__ == "__main__":
    main()
