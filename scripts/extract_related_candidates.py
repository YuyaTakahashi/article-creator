#!/usr/bin/env python3
"""
公開済み用語(glossary)の「関連用語」から、まだ用語として公開されていないものを
「用語作成候補」として抽出するローカル実行スクリプト。

Coworkサンドボックスからは外部HTTPSがブロックされるため、必ずローカル(Mac)で実行する。

使い方:
    cd ~/workspace/article-creator
    python3 scripts/extract_related_candidates.py

出力:
    - 標準出力: 候補サマリー(出現頻度順)
    - pipeline/related-term-candidates.json : 全候補データ(JSON)
    - pipeline/related-term-candidates.tsv  : シート貼り付け用(用語DB列順)
"""

import base64
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_env(env_path: Path) -> dict:
    env = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        env[k.strip()] = v.split("#")[0].strip() if "#" in v else v
    return env


def fetch_all_glossary(env):
    site = env["WP_SITE_URL"].rstrip("/")
    user = env["WP_USER"]
    app_pass = env["WP_APP_PASS"].replace(" ", "")
    post_type = env.get("WP_POST_TYPE", "glossary")
    auth = base64.b64encode(f"{user}:{app_pass}".encode()).decode()

    posts = []
    page = 1
    while True:
        q = urllib.parse.urlencode({
            "per_page": 100,
            "page": page,
            "status": "publish",
            "_fields": "id,slug,link,title,content",
        })
        url = f"{site}/wp-json/wp/v2/{post_type}?{q}"
        req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                batch = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 400:  # page out of range
                break
            sys.stderr.write(f"HTTP {e.code}: {e.read().decode(errors='replace')}\n")
            sys.exit(1)
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return posts


TAG_RE = re.compile(r"<[^>]+>")
PAREN_RE = re.compile(r"[（(].*?[）)]")
# サイト名・出典サフィックス( | UX TIMES / – Wikipedia / | Laws of UX 等)
SUFFIX_RE = re.compile(r"\s*[|｜–—-]\s*(UX\s*TIMES|Laws of UX|Wikipedia|ウィキペディア|Prototypr).*$", re.I)
ZEN2HAN = str.maketrans("０１２３４５６７８９", "0123456789")


def clean_text(s: str) -> str:
    s = html.unescape(s or "")
    s = TAG_RE.sub("", s)
    return s.strip()


def split_ja_en(s: str):
    """'ヒューマン・オン・ザ・ループ（Human-on-the-Loop）' -> (日本語, 英語)"""
    s = clean_text(s)
    s = SUFFIX_RE.sub("", s)         # 「| UX TIMES」等の出典サフィックスを除去
    s = re.sub(r"^UX\s*TIMES[\s\-–—]*", "", s, flags=re.I)  # 誤混入の接頭辞を除去
    m = PAREN_RE.search(s)
    en = ""
    if m:
        en = m.group(0).strip("（）()").strip()
    ja = PAREN_RE.sub("", s).strip().strip("・-–—:：（）() ").strip()
    return ja, en


def normalize_term(s: str) -> str:
    """日本語の用語名だけを取り出して照合キーにする(表記ゆれ吸収)。"""
    ja, _ = split_ja_en(s)
    ja = ja.translate(ZEN2HAN)               # 全角数字→半角
    ja = re.sub(r"[・／/、\s　]", "", ja)     # 区切り・空白を除去
    ja = ja.strip("・-–—:：").lower()
    return ja


# 用語候補として不適格な文字(混入した文章・引用・URL・書籍名などを弾く)
BAD_SUBSTR = ("http", "www.", "。", "？", "?", "！", "!", "「", "」", "『", "』",
              "：", ":", "wiki/", ".com", ".jp", ".org", "、")
SENTENCE_HINT = ("です", "ます", "ました", "ください", "でしょう", "という", "ため",
                 "こと", "できる", "される", "とは", "／心理", "危険な関係")


def is_term_like(ja: str) -> bool:
    """短く記号の少ない、用語らしい文字列だけを候補として残す。"""
    if not ja or len(ja) < 2 or len(ja) > 28:
        return False
    if not re.search(r"[\wぁ-んァ-ヶ一-龠]", ja):   # 記号のみは除外
        return False
    if any(b in ja for b in BAD_SUBSTR):
        return False
    if any(h in ja for h in SENTENCE_HINT):
        return False
    if re.search(r"(19|20)\d{2}", ja):        # 発行年を含む=引用
        return False
    if ja.count(" ") >= 3:                     # 英語の長文タイトル
        return False
    return True


def extract_related_block(content_html: str) -> str:
    """rendered contentから「関連用語」見出し以降〜次のh2手前を切り出す。"""
    idx = content_html.find("関連用語")
    if idx == -1:
        return ""
    tail = content_html[idx:]
    # 次のセクション見出し(h1〜h6のいずれか)手前まで = 関連用語ブロックのみ
    m = re.search(r"<h[1-6][ >]", tail[len("関連用語"):])
    if m:
        tail = tail[: m.start() + len("関連用語")]
    return tail


def extract_related_items(content_html: str):
    """関連用語ブロックから項目(text, href)を抽出。リンク形式・箇条書き形式の両方に対応。"""
    block = extract_related_block(content_html)
    if not block:
        return []
    items = []
    # 1) <a>リンク形式
    for m in re.finditer(r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>', block, re.S):
        href = m.group(1)
        text = clean_text(m.group(2))
        if text:
            items.append((text, href))
    if items:
        return items
    # 2) 箇条書き<li>形式(リンク無し)
    for m in re.finditer(r"<li[^>]*>(.*?)</li>", block, re.S):
        text = clean_text(m.group(1))
        if text:
            items.append((text, ""))
    return items


def norm_link(href: str) -> str:
    """glossaryパーマリンクを比較用に正規化。汎用インデックスは空扱い。"""
    if not href:
        return ""
    href = html.unescape(href).split("#")[0].split("?")[0].rstrip("/").lower()
    # 汎用インデックス(/articles/glossary で終わる)は「未作成リンク」なので除外
    if href.endswith("/articles/glossary") or href.endswith("/glossary"):
        return ""
    return href


def wp_search_glossary(env, term):
    """WP検索APIでglossary投稿を検索(公開済みの表記ゆれ検出用)。"""
    site = env["WP_SITE_URL"].rstrip("/")
    user = env["WP_USER"]
    app_pass = env["WP_APP_PASS"].replace(" ", "")
    post_type = env.get("WP_POST_TYPE", "glossary")
    auth = base64.b64encode(f"{user}:{app_pass}".encode()).decode()
    q = urllib.parse.urlencode({"search": term, "per_page": 5,
                                "status": "publish", "_fields": "title,link"})
    url = f"{site}/wp-json/wp/v2/{post_type}?{q}"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError:
        return []


def main():
    env = load_env(REPO / ".env")
    posts = fetch_all_glossary(env)
    print(f"公開済みglossary記事: {len(posts)}件を取得")

    published_keys = set()
    published_titles = {}
    published_links = set()
    for p in posts:
        t = clean_text(p.get("title", {}).get("rendered", ""))
        key = normalize_term(t)
        if key:
            published_keys.add(key)
            published_titles[key] = t
        ln = norm_link(p.get("link", ""))
        if ln:
            published_links.add(ln)

    # 既存シート行(すでにプール済み)を除外用に読む簡易リスト
    already_pooled = {
        normalize_term(x) for x in [
            "ヒューマン・イン・ザ・ループ", "ヒューマン・オン・ザ・ループ",
            "ダークパターン", "認知負荷",
        ]
    }

    candidates = {}  # key -> dict
    for p in posts:
        src_title = clean_text(p.get("title", {}).get("rendered", ""))
        content = p.get("content", {}).get("rendered", "")
        for text, href in extract_related_items(content):
            ja, en = split_ja_en(text)
            key = normalize_term(text)
            if not key:
                continue
            if not is_term_like(ja):
                continue  # 引用・書籍名・URL・文章などノイズを除外
            if key in published_keys:
                continue  # すでに公開済み
            c = candidates.setdefault(key, {
                "term": ja, "english": en, "count": 0,
                "sources": [], "hrefs": set(), "in_sheet": key in already_pooled,
            })
            c["count"] += 1
            if src_title not in c["sources"]:
                c["sources"].append(src_title)
            if en and not c["english"]:
                c["english"] = en
            if href:
                c["hrefs"].add(href)

    # === 再クリーニング: 公開済みの取りこぼしを厳密に除外 ===
    kept, removed = [], []
    for c in candidates.values():
        key = normalize_term(c["term"])
        reason = None
        # 1) 関連用語リンク先が実在の公開ページ = 公開済み
        for h in c["hrefs"]:
            if norm_link(h) in published_links:
                reason = "リンク先が公開ページ"
                break
        # 2) 正規化タイトルの完全一致(英語名併記・出典サフィックス等の表記ゆれ)
        #    ※部分一致は「モーダル⊂マルチモーダル」等の別用語を誤除外するため使わない
        if not reason and key in published_keys:
            reason = f"公開用語と完全一致: {published_titles.get(key, key)}"
        # 3) WP検索で同名の公開記事がヒット(送りがな違い等の取りこぼし・完全一致のみ)
        if not reason:
            for r in wp_search_glossary(env, c["term"]):
                rk = normalize_term(clean_text(r.get("title", {}).get("rendered", "")))
                if rk and rk == key:
                    reason = f"WP検索で公開ヒット: {clean_text(r.get('title',{}).get('rendered',''))}"
                    break
        if reason:
            c["removed_reason"] = reason
            removed.append(c)
        else:
            kept.append(c)

    ranked = sorted(kept, key=lambda x: (-x["count"], x["term"]))
    removed_sorted = sorted(removed, key=lambda x: (-x["count"], x["term"]))
    print(f"再クリーニング: 公開済みとして除外 {len(removed)}件 / 残り候補 {len(ranked)}件")

    # JSON出力
    out_json = []
    for c in ranked:
        out_json.append({
            "term": c["term"], "english": c["english"], "count": c["count"],
            "sources": c["sources"], "in_sheet_already": c["in_sheet"],
            "sample_hrefs": sorted(c["hrefs"])[:3],
        })
    (REPO / "pipeline" / "related-term-candidates.json").write_text(
        json.dumps({
            "generated_at": str(date.today()),
            "published_count": len(posts),
            "candidate_count": len(ranked),
            "removed_published_count": len(removed_sorted),
            "candidates": out_json,
            "removed_published": [
                {"term": c["term"], "english": c["english"], "count": c["count"],
                 "reason": c.get("removed_reason", "")}
                for c in removed_sorted
            ],
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    # TSV出力(用語DB列: ID/用語/英語名/補足・文脈/提案元/提案日/生成する/ステータス/記事Doc/WP URL/生成日/備考)
    today = str(date.today())
    lines = []
    next_id = 5  # G-004まで既存
    for c in ranked:
        if c["in_sheet"]:
            continue
        note = f"公開記事{c['count']}本の関連用語に登場（例: {c['sources'][0] if c['sources'] else ''}）"
        row = [
            f"G-{next_id:03d}", c["term"], c["english"],
            "関連用語ギャップから自動抽出", "関連用語抽出", today,
            "FALSE", "提案中", "", "", "", note,
        ]
        lines.append("\t".join(row))
        next_id += 1
    (REPO / "pipeline" / "related-term-candidates.tsv").write_text(
        "\n".join(lines) + "\n", encoding="utf-8")

    # サマリー表示
    print(f"\n未公開の関連用語(候補): {len(ranked)}件")
    print(f"うち既存シート未登録: {sum(1 for c in ranked if not c['in_sheet'])}件\n")
    print(f"{'#':>2}  {'出現':>3}  用語 / 英語名")
    print("-" * 60)
    for i, c in enumerate(ranked, 1):
        flag = " [既プール]" if c["in_sheet"] else ""
        en = f"  ({c['english']})" if c["english"] else ""
        print(f"{i:>2}  {c['count']:>3}   {c['term']}{en}{flag}")

    print(f"\n=== 公開済みとして除外した {len(removed_sorted)}件 ===")
    for c in removed_sorted:
        print(f"  - {c['term']}  ← {c.get('removed_reason','')}")
    print("\n出力: pipeline/related-term-candidates.json / .tsv")


if __name__ == "__main__":
    main()
