#!/usr/bin/env python3
"""
Geminiで生成したアイキャッチ画像に、cream beige の余白を上下左右に追加するローカル後処理スクリプト。

Geminiの画像生成はピクセル単位の座標指定を完全には守らないため、
生成後にこのスクリプトで「コンテンツを縮小→中央配置」して余白を確実に確保する。

使い方:
    cd ~/workspace/article-creator
    python3 scripts/add_eyecatch_padding.py drafts/FDE-eyecatch-v6.png
        # → drafts/FDE-eyecatch-v6-padded.png を生成

オプション:
    --ratio 0.65    元画像を65%に縮小（デフォルト）
    --bg "#F5EFE0"  余白の背景色（デフォルトはUX TIMESのクリームベージュ）
    --vshift 0.05   コンテンツを縦方向に少し下寄せ（0.0=中央, 正=下寄せ）
    --out path      出力先を明示指定（省略時は -padded サフィックス）
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow が見つかりません。`pip3 install Pillow` でインストールしてください。")


def hex_to_rgb(hex_str: str) -> tuple:
    h = hex_str.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Invalid hex color: {hex_str}")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def sample_background(src: Image.Image, sample_size: int = 30) -> tuple:
    """元画像の四隅 sample_size x sample_size 領域の平均色を背景色として抽出する。"""
    W, H = src.size
    s = sample_size
    regions = [
        src.crop((0, 0, s, s)),               # top-left
        src.crop((W - s, 0, W, s)),           # top-right
        src.crop((0, H - s, s, H)),           # bottom-left
        src.crop((W - s, H - s, W, H)),       # bottom-right
    ]
    totals = [0, 0, 0]
    count = 0
    for region in regions:
        for r, g, b in region.getdata():
            totals[0] += r
            totals[1] += g
            totals[2] += b
            count += 1
    return tuple(t // count for t in totals)


def add_padding(
    input_path: Path,
    output_path: Path,
    content_ratio: float = 0.82,
    bg_hex: str = None,
    v_shift: float = 0.0,
):
    src = Image.open(input_path).convert("RGB")
    W, H = src.size

    content_w = int(W * content_ratio)
    content_h = int(H * content_ratio)
    resized = src.resize((content_w, content_h), Image.LANCZOS)

    # 背景色：明示指定がなければ元画像から自動抽出
    if bg_hex:
        bg = hex_to_rgb(bg_hex)
        bg_source = f"explicit {bg_hex}"
    else:
        bg = sample_background(src)
        bg_source = f"auto-sampled #{bg[0]:02X}{bg[1]:02X}{bg[2]:02X}"
    canvas = Image.new("RGB", (W, H), bg)

    paste_x = (W - content_w) // 2
    paste_y = (H - content_h) // 2 + int(H * v_shift)
    paste_y = max(0, min(H - content_h, paste_y))

    canvas.paste(resized, (paste_x, paste_y))
    canvas.save(output_path, "PNG", optimize=True)
    print(f"✅ Saved: {output_path}")
    print(f"   Canvas: {W}x{H}, content area: {content_w}x{content_h}")
    print(f"   Background: {bg_source}")
    print(
        f"   Margins: top={paste_y}px, bottom={H - paste_y - content_h}px, "
        f"left={paste_x}px, right={W - paste_x - content_w}px"
    )


def main():
    parser = argparse.ArgumentParser(description="アイキャッチ画像にcream beige余白を追加")
    parser.add_argument("input", help="入力PNG画像のパス")
    parser.add_argument(
        "--ratio",
        type=float,
        default=0.82,
        help="コンテンツを元画像の何%に縮小するか（0.0〜1.0、デフォルト0.82）",
    )
    parser.add_argument(
        "--bg",
        default=None,
        help="余白の背景色（省略時は元画像の四隅から自動サンプリング）",
    )
    parser.add_argument(
        "--vshift",
        type=float,
        default=0.0,
        help="コンテンツを縦方向にシフト（0.0=中央, +0.05=少し下寄せ）",
    )
    parser.add_argument("--out", help="出力ファイル名（省略時は -padded サフィックス）")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        sys.exit(f"入力画像が見つかりません: {input_path}")

    if args.out:
        output_path = Path(args.out).resolve()
    else:
        output_path = input_path.with_name(input_path.stem + "-padded" + input_path.suffix)

    add_padding(input_path, output_path, args.ratio, args.bg, args.vshift)


if __name__ == "__main__":
    main()
