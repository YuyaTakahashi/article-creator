#!/usr/bin/env python3
"""
UX TIMES 用語集記事の「セクション・インフォグラフィック」を Gemini（Nano Banana）で生成する
ローカル実行スクリプト。アイキャッチ（generate_eyecatch.py）とは別に、本文の各セクション見出し
の直下に置く、章の要点を可視化したインフォグラフィックを作る。NotebookLM の動画オーバービュー
のような、白背景・幾何学フラット・ミニマルでモダンなテイストで統一する（こども向け・カートゥーン調に
しない）。短い日本語ラベルのみ可（サービス名・ロゴ・ウォーターマーク・cite 注釈は禁止）。アイキャッチの配色には寄せない。

Coworkサンドボックスからは外部HTTPSが403で叩けないため Mac 上で直接実行する。
Gemini呼び出しと .env 読み込みは generate_eyecatch.py の実装を再利用する。

使い方:
    cd ~/workspace/article-creator
    python3 scripts/generate_illustration.py \
        --prompt "a locked treasure chest with a small 'only 2 left' style scarcity aura, hands reaching" \
        --out drafts/artificial-scarcity-sec1.png

    # メタファーをファイルから渡す場合（長文・引用符対策）
    python3 scripts/generate_illustration.py --prompt-file /tmp/metaphor.txt --out drafts/xxx-sec2.png

出力:
    指定した --out に PNG を書き出す（frontmatterは触らない。本文への <figure> 挿入は呼び出し側が行う）。
"""

import argparse
import sys
from pathlib import Path

# 同じ scripts/ ディレクトリの generate_eyecatch から Gemini 呼び出しと .env ローダを再利用する
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_eyecatch import call_gemini_image, load_env  # noqa: E402


# セクション・インフォグラフィック用テンプレート。NotebookLM の動画オーバービューのような
# 白背景・幾何学フラット・こども向けキャッチーなテイストに統一する（アイキャッチには寄せない）。
# 短い日本語ラベルのみ可。サービス名・ロゴ・ウォーターマーク・cite 注釈は禁止。横長（16:9）構図。
SECTION_PROMPT_TEMPLATE = """Create an infographic that visualizes the key point of one section of a Japanese article, in the visual style of NotebookLM's video-overview illustrations — simple, friendly, catchy, easy enough for a child to understand at a glance. Compose as a horizontal banner (roughly 16:9).

STYLE — strict:
- Background: clean solid white (#FFFFFF), flat, with generous whitespace; never beige, never cream, no texture
- Flat design built from simple shapes with thin clean outlines and rounded, friendly forms
- Restrained accent colors on a mostly white canvas: soft blue as the main color, plus a little warm yellow / soft coral / soft green. No heavy gradients, no drop shadows, no 3D, no photorealism, no neon
- One main concept diagram centered, with plenty of breathing room around it

CONCRETENESS — the most common failure, avoid it:
- Draw RECOGNIZABLE EVERYDAY OBJECTS, not abstract dots, bars or generic tokens. A reader must grasp the point without reading the body text
- Prefer familiar things (a vending machine, a capsule-toy machine, a slot machine, a smartphone, a stamp card, a treasure chest) over featureless geometric markers
- Keep the objects simple and iconic, like friendly pictograms — cute and approachable is fine here, but never a mascot with a big-eyed face

TEXT — Japanese only, minimal:
- Place a few very short Japanese words as labels, using ONLY the exact Japanese words specified in SUBJECT below — no other text
- ABSOLUTELY NO English or Latin letters, NO service names or brand logos (never write "NotebookLM", "Google", etc.), NO watermarks, NO signatures, NO "cite" or citation-style annotations anywhere
- Keep any text to single short words or phrases; never full sentences

SUBJECT — visualize this key point as a simple centered infographic (do not draw literal UI screens):
{metaphor}

OUTPUT: clean, balanced, white-background infographic, catchy and child-friendly."""


def main():
    parser = argparse.ArgumentParser(description="Gemini でセクション装飾イラストを生成")
    parser.add_argument("--prompt", help="視覚メタファー（英語、1〜2文）")
    parser.add_argument("--prompt-file", help="メタファーをファイルから読む（--prompt の代わり）")
    parser.add_argument("--out", required=True, help="出力PNGパス（例: drafts/{slug}-sec1.png）")
    parser.add_argument("--raw", action="store_true",
                        help="テンプレートを使わず --prompt をそのまま画像プロンプトとして使う")
    args = parser.parse_args()

    if args.prompt_file:
        metaphor = Path(args.prompt_file).read_text(encoding="utf-8").strip()
    elif args.prompt:
        metaphor = args.prompt.strip()
    else:
        sys.exit("--prompt か --prompt-file を指定してください。")
    if not metaphor:
        sys.exit("メタファーが空です。")

    repo_root = Path(__file__).resolve().parent.parent
    env = load_env(repo_root / ".env")
    api_key = env.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY が .env に設定されていません。")

    prompt = metaphor if args.raw else SECTION_PROMPT_TEMPLATE.format(metaphor=metaphor)
    print("==== Prompt ====")
    print(prompt)
    print("================")
    print("Generating section illustration with Gemini...")

    image_bytes = call_gemini_image(api_key, prompt)

    out_path = (repo_root / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(image_bytes)
    print(f"✅ Saved: {out_path}")


if __name__ == "__main__":
    main()
