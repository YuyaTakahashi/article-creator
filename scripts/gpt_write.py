#!/usr/bin/env python3
"""article-creator の Step 4（初稿）と Step 5（整形）だけを OpenAI API で行う試験用スクリプト。

前提: Step 4 で Claude が research/{topic}_claims.md と research/{topic}_conditions.md を作り終えていること。
使い方: python3 scripts/gpt_write.py "{topic}" [--model {モデル名}]（既定は gpt-6.1-sol。10/17 のバイソシエーションと同じモデル）
出力:   pipeline/gpt/{topic}_turn1.md（初稿）、pipeline/gpt/{topic}_turn2.md（整形後＝Step 5 の完成稿）、
        pipeline/gpt/{topic}_turn3_{model}.md（読み手目線の書き直し。--no-turn3 で省略）
--turn3-only: 既存の turn1/turn2 を使い、turn3 だけを実行する
        pipeline/gpt/{topic}_meta.json（英語名 english と使ったモデル。drafts のフロントマター english に写す）
.env に OPENAI_API_KEY を置く。キーはこのスクリプトの外に出さない。
"""
import argparse, json, os, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

def load_env():
    for line in (REPO / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def chat(model, messages):
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({"model": model, "messages": messages}).encode(),
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]["content"]

HEAD1 = """あなたはUX TIMES用語集の執筆者です。
下の[出典台帳]と[成立条件メモ]は、すでに出典を読んで作成済みのものです。
Webを検索したり、あなた自身の知識で事実を足したりせず、台帳にある事実だけを使って、次の指示どおり初稿を書いてください。
前置きは不要です。初稿だけを出力してください。

# トピック
{topic}

"""

HEAD3 = """直前の記事を、この分野を初めて知る読者が一読で分かるように書き直してください。
事実は足さず、削らず、意味を変えないでください。見出しの構成（## の見出しの数と順番、「最小限の説明」「-- wp分割ライン--」「語源・提唱者」「関連用語」）は変えないでください。見出しの文言は、内容に合わせて分かりやすく直してかまいません。

1. 作品・事件・研究を例に使うときは、その中身（誰が何をしたか）を1〜2文で説明してから使う
2. 同じ抽象語（枠組み・構造・概念など）を3回以上続けて使わない。その場面に合う具体的な言葉に言い換える
3. 「〜から取り出され」「〜が統合され」のような抽象的な動きの文は、「誰が・何を・どうした」の文に直す
4. 各段落の最後に、その段落で読者が持ち帰る一文があるかを確かめ、なければ足す。足す一文は、その段落にすでに書いてあることのまとめに限る。台帳にない解釈・評価・一般化（「〜には〜の役割がある」など）は足さない。直前の文の言い直しにしかならないなら足さない（同じ内容を2回書かない）
5. 導入文は「（用語）とは、〜である」の定義文を軸にし、その直後に、読者が思い浮かべられる具体例や問いを置く。定義文に読者の知らない語が残るときは、台帳の（前提）を使った1〜2文を定義文の前に置いてよい
6. 専門用語（一般の国語辞典に載っていない語・その業界でしか使わない語）は、初めて出る箇所で、台帳の（働き）を使って「何をするためのものか」で言い換える。仕組みは台帳の（手計算）か（たとえ）で見せ、起きることは（結果）の言葉で言う。英字の略語も初めて出る箇所で日本語に開く。読者の想定は、難易度 difficulty={difficulty}（0=中学生、1=専門家）、IT知識 it={it}（0=一般ユーザー、1=熟練エンジニア）。言い換えは台帳の事実の範囲で行い、新しい事実を足さない

前置きは不要です。書き直した記事だけを出力してください。
"""


HEAD_EN = """この用語の英語名を1行だけ出力してください。
[出典台帳]の英語の出典がこの用語を呼ぶときの呼び方を使い（単語の頭は大文字にそろえる）、日本語の見出しに合わせて語を足さないでください（例:「ホットハンド現象」なら Hot Hand）。
英語の呼び方が台帳に無い日本独自の用語なら、何も出力しないでください。英語名以外の文字（説明・引用符・句点）は出力しないでください。
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--difficulty", default="0.3")
    ap.add_argument("--it", default="0.3")
    ap.add_argument("--no-turn3", action="store_true")
    ap.add_argument("--turn3-only", action="store_true")
    a = ap.parse_args()
    load_env()

    claims = (REPO / f"research/{a.topic}_claims.md").read_text()
    conds = (REPO / f"research/{a.topic}_conditions.md").read_text()
    if a.turn3_only and "## 追記（" in claims:
        # turn2 を作った時点の台帳にそろえる（公開作業で足した追記を入れない）
        claims = claims[:claims.index("## 追記（")]
    p01 = (REPO / "prompts/01_information_gathering.md").read_text()
    p02 = (REPO / "prompts/02_polishing.md").read_text()

    t1 = HEAD1.format(topic=a.topic) + p01[p01.index("# 出力3：初稿"):] + \
        f"\n\n### [出典台帳]\n{claims}\n\n### [成立条件メモ]\n{conds}\n"
    t2 = (p02.replace("{difficulty}", a.difficulty).replace("{it}", a.it)
             .replace("{claims}", claims).replace("{conditions}", conds)
             .replace("{draft}", "（直前のメッセージであなたが書いた初稿を使う）"))

    out = REPO / "pipeline/gpt"
    out.mkdir(parents=True, exist_ok=True)
    msgs = [{"role": "user", "content": t1}]
    if a.turn3_only:
        draft = (out / f"{a.topic}_turn1.md").read_text()
        final = (out / f"{a.topic}_turn2.md").read_text()
        msgs += [{"role": "assistant", "content": draft}, {"role": "user", "content": t2}]
    else:
        draft = chat(a.model, msgs)
        (out / f"{a.topic}_turn1.md").write_text(draft)
        msgs += [{"role": "assistant", "content": draft}, {"role": "user", "content": t2}]
        final = chat(a.model, msgs)
        (out / f"{a.topic}_turn2.md").write_text(final)
        print(f"saved: pipeline/gpt/{a.topic}_turn1.md, pipeline/gpt/{a.topic}_turn2.md (model={a.model})")
    if not a.no_turn3:
        msgs += [{"role": "assistant", "content": final}, {"role": "user", "content":
                 HEAD3.replace("{difficulty}", a.difficulty).replace("{it}", a.it)}]
        final = chat(a.model, msgs)
        (out / f"{a.topic}_turn3_{a.model}.md").write_text(final)
        print(f"saved: pipeline/gpt/{a.topic}_turn3_{a.model}.md (model={a.model})")
    english = chat(a.model, msgs + [{"role": "assistant", "content": final},
                                    {"role": "user", "content": HEAD_EN}]).strip().strip('"').strip()
    (out / f"{a.topic}_meta.json").write_text(
        json.dumps({"english": english, "writer_model": a.model}, ensure_ascii=False, indent=1))
    print(f"saved: pipeline/gpt/{a.topic}_meta.json (english={english or '（なし）'})")
    return

if __name__ == "__main__":
    main()
