#!/usr/bin/env python3
"""
UX TIMES 用語集記事のアイキャッチを Gemini 2.5 Flash Image（通称 Nano Banana）で生成する
ローカル実行スクリプト。Coworkサンドボックスからは外部HTTPSが403で叩けないため、
Mac上で直接実行する。

使い方:
    cd ~/workspace/article-creator
    python3 scripts/generate_eyecatch.py drafts/FDE.md
        --metaphor "A casual engineer with laptop converses with a business executive..."
        --objects "engineer in hoodie, executive in suit, speech bubbles"
        --type "two-person dialogue"

引数を省略した場合は、フロントマターの eyecatch_prompt フィールドからメタファーを自動抽出する。

事前準備:
    1. Google AI Studio (https://aistudio.google.com/apikey) で API キーを発行
    2. .env に GEMINI_API_KEY=xxx を追加

出力:
    drafts/{topic-slug}-eyecatch.png (1024x1024)
    フロントマターの eyecatch_image フィールドに相対パスを追記
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path


GEMINI_MODEL = "gemini-3-pro-image"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

PROMPT_TEMPLATE = """A square (1:1) editorial illustration for a Japanese UX glossary article.

STYLE — strict:
- Background: warm cream beige (#F5EFE0), flat, no texture
- Composition type: {illustration_type}
- Color palette: limited to 3–4 colors — beige background (#F5EFE0), black outlines (#1A1A1A), soft blue-gray fills (#7A8DA0), and optionally one accent of muted mustard (#C9A35E) or moss green (#8FA68C)
- Style: flat, minimalist, line-art with subtle fills, modern editorial, generous whitespace
- No gradients, no drop shadows, no photorealism, no neon, no harsh colors
- Text: ONLY the title "{title_jp}" in bold Japanese sans-serif (Noto Sans JP style), centered horizontally in the upper-middle band, black color, about 7% of the canvas height
- No other text, labels, watermarks, captions, or signatures anywhere

LAYOUT — OGP-safe, generous top margin (CRITICAL):
Twitter/X large cards crop the square to 1.91:1 (center crop), cutting roughly the top 24% and bottom 24%. So ALL content (title AND illustration) MUST stay inside the central vertical band y=240–780 of the 1024px canvas. Keep the top and bottom margins as continuous cream beige (#F5EFE0), never white.
- 0–240px (top edge): cream beige background only. ABSOLUTELY NO title or illustration here. This is the OGP-clipped safe margin.
- 240–380px: the title text "{title_jp}", centered horizontally, sitting fully inside the OGP-visible band (do NOT place the title against the very top edge).
- 380–780px: the main illustration, centered.
- 780–1024px (bottom edge): cream beige background only. No content here.
The entire canvas, including the top and bottom margins, is one continuous cream beige (#F5EFE0) — edge to edge, never white.

SUBJECT:
{core_metaphor}

KEY VISUAL ELEMENTS:
{key_objects}

OUTPUT: 1024x1024 PNG, clean and balanced composition."""


# ---------- .env / フロントマター ----------

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
        env[k.strip()] = v
    return env


def parse_frontmatter(md_text: str) -> dict:
    if not md_text.startswith("---"):
        return {}
    parts = md_text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        fm[k.strip()] = v
    return fm


# ---------- Gemini 呼び出し ----------

def call_gemini_image(api_key: str, prompt: str) -> bytes:
    """Gemini 2.5 Flash Image を呼び出して PNG バイナリを返す。"""
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "candidateCount": 1,
        },
    }
    url = f"{GEMINI_ENDPOINT}?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP {e.code} error:\n{e.read().decode()}\n")
        sys.exit(1)

    # レスポンスから inline_data (base64) を取り出す
    candidates = body.get("candidates", [])
    if not candidates:
        sys.stderr.write(f"No candidates returned: {json.dumps(body)[:800]}\n")
        sys.exit(1)
    for part in candidates[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"])
    sys.stderr.write(f"No image in response: {json.dumps(body)[:800]}\n")
    sys.exit(1)


# ---------- フロントマター更新 ----------

def append_eyecatch_path(md_path: Path, rel_path: str):
    text = md_path.read_text(encoding="utf-8")
    if "eyecatch_image:" in text:
        # 既存値を置換
        text = re.sub(r"eyecatch_image:[^\n]*", f'eyecatch_image: "{rel_path}"', text)
    else:
        # フロントマター末尾に追加
        text = re.sub(
            r"(^---\n.*?)(\n---)",
            lambda m: f'{m.group(1)}\neyecatch_image: "{rel_path}"{m.group(2)}',
            text,
            count=1,
            flags=re.DOTALL,
        )
    md_path.write_text(text, encoding="utf-8")


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(description="Gemini Nano Banana でアイキャッチを生成")
    parser.add_argument("md_path", help="drafts/{topic}.md")
    parser.add_argument("--metaphor", help="CORE_METAPHOR（省略時はeyecatch_promptから抽出）")
    parser.add_argument("--objects", help="KEY_OBJECTS（カンマ区切り、英語）")
    parser.add_argument(
        "--type",
        default="conceptual diagram with arrows",
        choices=["two-person dialogue", "conceptual diagram with arrows", "abstract infographic"],
        help="ILLUSTRATION_TYPE",
    )
    parser.add_argument("--out", help="出力ファイル名（省略時 drafts/{slug}-eyecatch.png）")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    md_path = (repo_root / args.md_path).resolve()
    if not md_path.exists():
        sys.exit(f"MDファイルが見つかりません: {md_path}")

    env = load_env(repo_root / ".env")
    api_key = env.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY が .env に設定されていません。\nhttps://aistudio.google.com/apikey で発行してください。")

    md_text = md_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(md_text)
    title_jp = re.split(r"[（(]", fm.get("title", md_path.stem))[0].strip()

    metaphor = args.metaphor or fm.get("eyecatch_prompt", "")
    if not metaphor:
        sys.exit("--metaphor を指定するか、フロントマターに eyecatch_prompt を入れてください。")

    objects = args.objects or "main symbol of the term, supporting icons, connecting lines or arrows"

    prompt = PROMPT_TEMPLATE.format(
        illustration_type=args.type,
        title_jp=title_jp,
        core_metaphor=metaphor,
        key_objects=objects,
    )
    print("==== Prompt ====")
    print(prompt)
    print("================")
    print("Generating image with Gemini Nano Banana...")

    image_bytes = call_gemini_image(api_key, prompt)

    # 出力ファイル名は英語slug基準にする（日本語ファイル名はWPアップロード時にヘッダで落ちるため）
    slug = fm.get("slug") or md_path.stem
    out_name = args.out or f"{slug}-eyecatch.png"
    out_path = md_path.parent / out_name
    out_path.write_bytes(image_bytes)
    print(f"✅ Saved: {out_path}")

    # フロントマターに追記
    rel = f"drafts/{out_path.name}"
    append_eyecatch_path(md_path, rel)
    print(f"✅ Frontmatter updated: eyecatch_image: {rel}")


if __name__ == "__main__":
    main()
