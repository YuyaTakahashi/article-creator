#!/usr/bin/env python3
"""
UX TIMES 用語集記事の「セクション装飾イラスト」を Gemini（Nano Banana）で生成する
ローカル実行スクリプト。アイキャッチ（generate_eyecatch.py）とは別に、本文の各セクション見出し
の直下に置く装飾イラストを作る。文字を一切入れない・アイキャッチと同じフラットな配色で統一する。

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


# セクション装飾イラスト用テンプレート。アイキャッチと配色を揃えつつ、
# タイトル文字を入れない・横長バナー寄りの構図にする（本文インライン用）。
SECTION_PROMPT_TEMPLATE = """A minimalist editorial spot illustration for a Japanese UX glossary article, composed as a horizontal banner (roughly 16:9).

STYLE — strict:
- Background: warm cream beige (#F5EFE0), flat, edge to edge, no texture, never white
- Color palette: 3-4 colors only — beige background (#F5EFE0), charcoal outlines (#1A1A1A), soft blue-gray fills (#7A8DA0), and optionally one muted accent (mustard #C9A35E or moss green #8FA68C)
- Flat, minimalist line-art with subtle fills, thick charcoal outlines, generous whitespace
- No gradients, no drop shadows, no photorealism, no neon, no harsh colors
- ABSOLUTELY NO text, letters, numbers, labels, captions, watermarks, or signatures anywhere in the image

SUBJECT — a simple, abstract visual metaphor for this section (do not draw literal UI screens):
{metaphor}

Compose with breathing room rather than filling the frame.
OUTPUT: clean, balanced, decorative spot illustration."""


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
