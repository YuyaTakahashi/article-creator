#!/usr/bin/env python3
"""A〜Dをブラインド化する。出どころの手がかり（フロントマター・ルビ記法・utmタグ・箇条書き記号）をそろえて、順番をシャッフルする。
対応表は _key.json に書く（評価が終わるまで開かない）。"""
import json, random, re
from pathlib import Path

OUT = Path(__file__).resolve().parent
TERMS = {"jailbreaking": "ジェイルブレイク", "active-learning": "アクティブラーニング", "agentic-rag": "エージェンティックRAG"}
SRC = {"A": "A_claude_pipeline.md", "B": "B_gpt_full.md", "C": "C_gpt_minimal.md", "D": "D_claude_full.md"}

def normalize(text, title):
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)          # フロントマター
    text = re.sub(r"^# .*\n", "", text, flags=re.M)                     # 既存タイトル行
    text = text.replace("?utm_source=chatgpt.com", "")
    text = re.sub(r"([A-Za-z.]+)[¥\\]([^¥\\\s]+)[¥\\]\s?", r"\1（\2）", text)  # ルビ → 英字（カナ）
    text = re.sub(r"^\* ", "- ", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return f"# {title}\n\n{text}\n"

bd = OUT / "blind"
bd.mkdir(exist_ok=True)
# 用語ごとに独立にシャッフルしつつ、同じ番号に同じ作成元が2用語以上で重ならないようにする
while True:
    orders = [random.sample(list(SRC), 4) for _ in TERMS]
    if all(len({o[i] for o in orders}) == len(orders) for i in range(4)):
        break
key = {}
sheet = ["# 評価シート", "", "各用語の記事1〜4を読み、次の2つを付ける。", "",
         "- 修正レベル：この版を公開まで持っていくなら、1〜3のどれか（article-edit-retro と同じ物差し）",
         "- いちばん読みやすい記事の番号", ""]
for slug, title in TERMS.items():
    labels = orders[list(TERMS).index(slug)]
    key[slug] = {f"記事{i+1}": lab for i, lab in enumerate(labels)}
    parts = []
    for i, lab in enumerate(labels):
        body = normalize((OUT / slug / "outputs" / SRC[lab]).read_text(), title)
        body = body.replace(f"# {title}", f"# 記事{i+1}：{title}", 1)
        parts.append(body)
    (bd / f"{title}.md").write_text("\n\n---\n\n".join(parts))
    sheet += [f"## {title}", "", "| 記事 | 修正レベル | メモ |", "|---|---|---|"]
    sheet += [f"| 記事{i+1} |  |  |" for i in range(4)]
    sheet += ["", "いちばん読みやすい：記事", ""]
(bd / "評価シート.md").write_text("\n".join(sheet))
(OUT / "_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2))
print("done")
