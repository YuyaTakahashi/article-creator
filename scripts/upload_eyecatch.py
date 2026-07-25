#!/usr/bin/env python3
"""
WordPress を「正」とみなして、アイキャッチ（featured_media）だけを既存記事に載せる
ローカル実行スクリプト。

post_to_wp.py の更新モードは title / content / excerpt / category をローカルMDで丸ごと
上書きするため、WP側で編集された本文があると消えてしまう。本スクリプトは本文・タイトル等に
一切触れず、featured_media フィールドだけを PATCH する。WP本文を正として保ったまま
アイキャッチを差し替える用途に使う。

使い方:
    cd ~/workspace/article-creator
    python3 scripts/upload_eyecatch.py drafts/{filename}.md

前提:
- フロントマターに wp_post_id（対象記事）と eyecatch_image（ローカル画像パス）があること。
- featured_media が既にあれば、その media をそのまま再設定する（再アップロードしない）。
"""

import sys
import json
import base64
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from post_to_wp import load_env, parse_frontmatter, upload_media  # noqa: E402


def patch_featured_media(env: dict, post_id: str, media_id: int):
    site = env["WP_SITE_URL"].rstrip("/")
    user = env["WP_USER"]
    app_pass = env["WP_APP_PASS"].replace(" ", "")
    post_type = env.get("WP_POST_TYPE", "posts")
    auth = base64.b64encode(f"{user}:{app_pass}".encode()).decode()

    # featured_media だけを送る。content/title/excerpt は送らないので WP本文は不変。
    payload = {"featured_media": int(media_id)}
    endpoint = f"{site}/wp-json/wp/v2/{post_type}/{post_id}"
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP {e.code} error:\n{e.read().decode()}\n")
        sys.exit(1)


def add_featured_media_to_md(md_path: Path, media_id: int):
    text = md_path.read_text(encoding="utf-8")
    if "featured_media:" in text:
        return
    new_lines = []
    inserted = False
    for line in text.splitlines():
        new_lines.append(line)
        if (not inserted) and line.startswith("eyecatch_image:"):
            new_lines.append(f"featured_media: {media_id}")
            inserted = True
    md_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("usage: python3 scripts/upload_eyecatch.py drafts/{filename}.md\n")
        sys.exit(2)

    repo_root = Path(__file__).resolve().parent.parent
    env = load_env(repo_root / ".env")

    md_path = (repo_root / sys.argv[1]).resolve()
    if not md_path.exists():
        sys.stderr.write(f"MDファイルが見つかりません: {md_path}\n")
        sys.exit(1)

    fm, _ = parse_frontmatter(md_path.read_text(encoding="utf-8"))
    post_id = fm.get("wp_post_id")
    if not post_id:
        sys.stderr.write("wp_post_id がありません。先に記事を作成してください（post_to_wp.py）。\n")
        sys.exit(1)

    media_id = fm.get("featured_media")
    if media_id:
        print(f"[media] 既存 featured_media={media_id} を再設定します（再アップロードなし）")
    else:
        eyecatch = fm.get("eyecatch_image", "")
        if not eyecatch.startswith("drafts/"):
            sys.stderr.write("eyecatch_image（drafts/配下）がありません。先にアイキャッチを生成してください。\n")
            sys.exit(1)
        ec_path = (repo_root / eyecatch).resolve()
        if not ec_path.exists():
            sys.stderr.write(f"アイキャッチ画像が見つかりません: {eyecatch}\n")
            sys.exit(1)
        media_id, source_url = upload_media(env, ec_path)
        print(f"[media] アップロード: {eyecatch} -> media id={media_id} ({source_url})")
        add_featured_media_to_md(md_path, media_id)

    status, body = patch_featured_media(env, post_id, media_id)
    site = env["WP_SITE_URL"].rstrip("/")
    print("\n==== 結果（WordPressを正・本文は不変）====")
    print(f"HTTP          : {status}")
    print(f"対象記事ID    : {post_id}")
    print(f"featured_media: {media_id}")
    print(f"WP編集URL     : {site}/wp-admin/post.php?post={post_id}&action=edit")


if __name__ == "__main__":
    main()
