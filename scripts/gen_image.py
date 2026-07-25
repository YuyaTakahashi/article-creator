#!/usr/bin/env python3
"""
任意プロンプトで画像を1枚生成する汎用ローカルスクリプト（Gemini 2.5 Flash Image / Nano Banana）。
章ごとの挿絵生成など、generate_eyecatch.py 以外の画像生成に使う。

使い方:
    cd ~/workspace/article-creator
    python3 scripts/gen_image.py --out drafts/images/foo/1.png --prompt "A flat illustration ..."

事前準備: .env に GEMINI_API_KEY=xxx
"""

import argparse
import base64
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

GEMINI_MODEL = "gemini-3-pro-image"
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)


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


def call_gemini_image(api_key: str, prompt: str) -> bytes:
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "candidateCount": 1},
    }
    req = urllib.request.Request(
        f"{GEMINI_ENDPOINT}?key={api_key}",
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
    candidates = body.get("candidates", [])
    if not candidates:
        sys.stderr.write(f"No candidates: {json.dumps(body)[:800]}\n")
        sys.exit(1)
    for part in candidates[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            return base64.b64decode(inline["data"])
    sys.stderr.write(f"No image in response: {json.dumps(body)[:800]}\n")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    env = load_env(repo_root / ".env")
    api_key = env.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY が .env にありません。")

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = (repo_root / out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    image_bytes = call_gemini_image(api_key, args.prompt)
    out_path.write_bytes(image_bytes)
    print(f"OK {out_path} ({len(image_bytes)} bytes)")


if __name__ == "__main__":
    main()
