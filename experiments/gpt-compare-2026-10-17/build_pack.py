#!/usr/bin/env python3
"""ChatGPT比較実験用のプロンプトパックを組み立てる（2026-10-17）。
入力はリポジトリ内の既存ファイルのみ。プロンプト本文は prompts/ から機械的に切り出す。"""
import json, re, html, urllib.request
from pathlib import Path

REPO = Path.home() / "workspace/article-creator"
OUT = Path(__file__).resolve().parent
TERMS = [  # (topic, slug)
    ("ジェイルブレイク", "jailbreaking"),
    ("アクティブラーニング", "active-learning"),
    ("agentic RAG", "agentic-rag"),
]
DIFF = IT = "0.3"  # バッチ・generate-term と同じ既定値

p01 = (REPO / "prompts/01_information_gathering.md").read_text()
p02 = (REPO / "prompts/02_polishing.md").read_text()
draft_part = p01[p01.index("# 出力3：初稿"):]

HEAD1 = """あなたはUX TIMES用語集の執筆者です。
下の[出典台帳]と[成立条件メモ]は、すでに出典を読んで作成済みのものです。
Webを検索したり、あなた自身の知識で事実を足したりせず、台帳にある事実だけを使って、次の指示どおり初稿を書いてください。
前置きは不要です。初稿だけを出力してください。

# トピック
{topic}

"""

MINIMAL = """あなたはUX TIMES（UX DAYS TOKYO）の用語集記事の執筆者です。
「{topic}」の用語解説記事を書いてください。

守ることは3つだけです。
1. 事実は、下の[出典台帳]にあるものだけを使う。Web検索や自分の知識で事実を足さない。
2. その分野を初めて知る人が、一読で分かる文章にする。
3. 「だ・である」調で書く。

構成は次の見出しに沿ってください（{{ }}の見出しは内容に合わせて書き換える）。

```
## 最小限の説明
（20〜35文字で用語を定義する。句点なし）

-- wp分割ライン--

（見出しなしの導入文）

## {{定義や本質を表す見出し}}
## 語源・提唱者
## {{効果や現れ方を表す見出し}}
## {{実務でどう使われるかを表す見出し}}
## 関連用語
```

前置きは不要です。記事だけを出力してください。

### [出典台帳]
{claims}

### [成立条件メモ]
{conditions}
"""

def fetch_published(slug):
    url = f"https://uxdaystokyo.com/articles/wp-json/wp/v2/glossary?slug={slug}&_fields=title,content,link"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))[0]
    body = d["content"]["rendered"]
    body = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", body, flags=re.S)
    body = re.sub(r"<(br|/p|/li|/blockquote)[^>]*>", "\n", body)
    body = re.sub(r"<li[^>]*>", "- ", body)
    body = html.unescape(re.sub(r"<[^>]+>", "", body))
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return f"# {html.unescape(d['title']['rendered'])}\n\n公開URL: {d['link']}\n\n{body}\n"

for topic, slug in TERMS:
    claims = (REPO / f"research/{topic}_claims.md").read_text()
    conds = (REPO / f"research/{topic}_conditions.md").read_text()
    d = OUT / slug
    (d / "outputs").mkdir(parents=True, exist_ok=True)

    t1 = HEAD1.format(topic=topic) + draft_part + \
        f"\n\n### [出典台帳]\n{claims}\n\n### [成立条件メモ]\n{conds}\n"
    t2 = (p02.replace("{difficulty}", DIFF).replace("{it}", IT)
             .replace("{claims}", claims).replace("{conditions}", conds)
             .replace("{draft}", "（直前のメッセージであなたが書いた初稿を使う）"))
    (d / "1_full_turn1.txt").write_text(t1)
    (d / "1_full_turn2.txt").write_text(t2)
    (d / "2_minimal.txt").write_text(MINIMAL.format(topic=topic, claims=claims, conditions=conds))

    a = (REPO / f"drafts/_baseline/{topic}_v19.md").read_text()
    (d / "outputs/A_claude_pipeline.md").write_text(a)
    try:
        (d / "outputs/REF_published.md").write_text(fetch_published(slug))
        pub = "ok"
    except Exception as e:
        pub = f"取得失敗: {e}"
    print(f"{topic}: turn1={len(t1)}字 turn2={len(t2)}字 minimal={len((d/'2_minimal.txt').read_text())}字 公開版={pub}")
