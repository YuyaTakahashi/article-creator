#!/usr/bin/env python3
"""下書きMDの <figure> をDoc用の本文から外し、提唱者の肖像だけを用語DBへ渡せる形に取り出す。

肖像をDocに入れると、Googleドキュメント側で画像とキャプションが次の段落と1つにつながる。
用語くん（pipeline/glossary-bot/code.js）はDocの画像を読まないので、WP下書きには
「〇〇（出典：URL） これによって、…」のようにキャプションの文字だけが本文の頭に残っていた。

そこで次のように分ける。
- Docには <figure> を一切入れない（挿絵も同じ理由で入れない。挿絵は⑤の画像入れで足す）
- `## 語源・提唱者` の中にある <figure> は肖像として、用語DBのX列にJSONで控える
- 用語くんがWP下書きにするとき、X列を読んで元の位置の近くへ差し込む

差し込む位置の目印（after）は、肖像の人物の英字の姓（ルビ記法 `Hegel¥ヘーゲル¥` の Hegel）にする。
直前の段落の文言そのものを目印にすると、レビューで1字直しただけで位置を見失うため。
"""

import json
import re

FIGURE_RE = re.compile(r"<figure\b.*?</figure>", re.S)
HEADING_RE = re.compile(r"^#{1,4}\s+(.*)$")
ORIGIN_HEADING = "語源"
ALT_RE = re.compile(r'\balt="([^"]*)"')
SRC_RE = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"')
RUBY_RE = re.compile(r"([A-Za-z][A-Za-z.'’\-]*)[¥￥]([^¥￥\n]+)[¥￥]")


def _surname_key(alt, context):
    """肖像の alt（カタカナ氏名）から、本文で人物を探すための英字の姓を決める。

    本文に見つからない語は目印にしない（空を返し、呼び出し側が直前の段落で代える）。
    """
    name = re.split(r"[｜|]", re.sub(r"[（(].*?[）)]", "", alt))[0]
    tokens = [t for t in re.split(r"[・＝=\s　]", name) if t]
    surname = tokens[-1] if tokens else ""
    if not surname:
        return ""
    for en, kana in RUBY_RE.findall(context):
        if kana == surname:
            return en
    return surname if surname in context else ""


def _fallback_key(paragraph):
    """姓が決められないときは、直前の段落の書き出しを目印にする。"""
    plain = RUBY_RE.sub(r"\1", paragraph).strip()
    return plain[:12]


def split_figures(body):
    """本文から <figure> をすべて外し、(外した本文, 肖像のリスト) を返す。

    肖像は [{"html": "<figure …>", "src": "…", "after": "Hegel"}] の形。
    html は改行を詰めて1行にする（用語くんの変換は「< で始まる行」を生HTMLとして素通しするため）。
    """
    portraits = []
    out_lines = []
    section = ""
    last_para = ""
    # figure が複数行にまたがっていても拾えるよう、先に figure を1行の印へ置き換えておく
    figures = []

    def stash(m):
        figures.append(m.group(0))
        return f"\n\x00FIG{len(figures) - 1}\x00\n"

    marked = FIGURE_RE.sub(stash, body)
    section_text = {}
    for line in marked.split("\n"):
        h = HEADING_RE.match(line)
        if h:
            section = h.group(1).strip()
        section_text.setdefault(section, []).append(line)

    section = ""
    for line in marked.split("\n"):
        h = HEADING_RE.match(line)
        if h:
            section = h.group(1).strip()
            last_para = ""
        m = re.fullmatch(r"\x00FIG(\d+)\x00", line.strip())
        if m:
            html = figures[int(m.group(1))]
            if section.startswith(ORIGIN_HEADING):
                one_line = re.sub(r"\s*\n\s*", " ", html).strip()
                alt = (ALT_RE.search(html) or [None, ""])[1]
                src = (SRC_RE.search(html) or [None, ""])[1]
                context = "\n".join(section_text.get(section, []))
                key = _surname_key(alt, context) or _fallback_key(last_para)
                portraits.append({"html": one_line, "src": src, "after": key})
            continue
        if line.strip():
            last_para = line
        out_lines.append(line)

    text = "\n".join(out_lines)
    # figure を外した跡に空行が重なるので、3行以上の空行は2行に詰める
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text, portraits


def portraits_json(body):
    """用語DBのX列に書く文字列。肖像が無いときも "[]" を返し、作り直しで古い肖像が残らないようにする。"""
    _, portraits = split_figures(body)
    return json.dumps(portraits, ensure_ascii=False)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    for p in sys.argv[1:]:
        print(p, portraits_json(Path(p).read_text(encoding="utf-8")))
