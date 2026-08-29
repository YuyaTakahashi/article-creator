#!/usr/bin/env python3
"""
drafts/{filename}.md を読み込み、HTMLに変換してWordPressに投稿するローカル実行スクリプト。

Coworkサンドボックスからは外部HTTPSがプロキシでブロックされるため、
記事生成/Critic検証はCowork側で行い、最終POSTだけこのスクリプトをローカルで実行する。

使い方:
    cd ~/workspace/article-creator
    python3 scripts/post_to_wp.py drafts/FDE.md
    python3 scripts/post_to_wp.py drafts/FDE.md --media-only

挙動:
- フロントマターに wp_post_id が無ければ新規下書き作成
- ある場合は更新
- 新規作成成功時、wp_post_id をフロントマターに自動追記する
- `--media-only` を付けると、本文/タイトル/抜粋/カテゴリは触らずに featured_media
  だけを差し替える（WP側で加筆された本文を上書きしないための保護オプション）
"""

import sys
import os
import re
import json
import base64
import mimetypes
import urllib.request
import urllib.error
from pathlib import Path


# ---------- .env 読み込み ----------

def load_env(env_path: Path) -> dict:
    env = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        # 値の前後のクォートを剥がす
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        env[k.strip()] = v
    return env


# ---------- Markdown → HTML 変換 ----------

# ルビの区切りは半角¥(U+00A5)と全角￥(U+FFE5)の両方を受ける（記事によって書かれ方が揺れるため）
RUBY_RE = re.compile(r"([A-Za-z0-9.\-]+)[¥￥]([^¥￥]+)[¥￥]")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
EM_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def inline_format(text: str) -> str:
    text = RUBY_RE.sub(r"<ruby>\1<rt>\2</rt></ruby>", text)
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = EM_RE.sub(r"<em>\1</em>", text)
    text = LINK_RE.sub(r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text


def parse_frontmatter(md_text: str):
    if not md_text.startswith("---"):
        return {}, md_text
    parts = md_text.split("---", 2)
    if len(parts) < 3:
        return {}, md_text
    raw_fm = parts[1]
    body = parts[2].lstrip("\n")
    fm = {}
    for line in raw_fm.strip().splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        fm[k.strip()] = v
    return fm, body


def _table_cells(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_table_separator(line: str) -> bool:
    cells = _table_cells(line)
    if not cells:
        return False
    return all(c and set(c) <= set("-: ") and "-" in c for c in cells)


def md_to_html(md_body: str) -> str:
    # -- wp分割ライン-- より後ろが本文
    sep = "-- wp分割ライン--"
    if sep in md_body:
        md_body = md_body.split(sep, 1)[1].lstrip("\n")

    lines = md_body.splitlines()
    html_parts = []
    para_buf = []
    list_buf = []
    blockquote_buf = []
    table_buf = []

    def flush_para():
        if para_buf:
            text = " ".join(para_buf).strip()
            if text:
                html_parts.append(f"<p>{inline_format(text)}</p>")
            para_buf.clear()

    def flush_list():
        if list_buf:
            items = "".join(f"<li>{inline_format(x)}</li>" for x in list_buf)
            html_parts.append(f"<ul>{items}</ul>")
            list_buf.clear()

    def flush_quote():
        if blockquote_buf:
            content = "<br>".join(inline_format(x) for x in blockquote_buf)
            html_parts.append(f"<blockquote>{content}</blockquote>")
            blockquote_buf.clear()

    def flush_table():
        if not table_buf:
            return
        rows = table_buf[:]
        table_buf.clear()
        header = None
        if len(rows) >= 2 and _is_table_separator(rows[1]):
            header = _table_cells(rows[0])
            body_rows = [_table_cells(r) for r in rows[2:]]
        else:
            body_rows = [_table_cells(r) for r in rows]
        out = ["<table>"]
        if header:
            out.append(
                "<thead><tr>"
                + "".join(f"<th>{inline_format(c)}</th>" for c in header)
                + "</tr></thead>"
            )
        out.append("<tbody>")
        for r in body_rows:
            out.append(
                "<tr>" + "".join(f"<td>{inline_format(c)}</td>" for c in r) + "</tr>"
            )
        out.append("</tbody></table>")
        html_parts.append("".join(out))

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        # 表の行（| ... |）はまとめてバッファし、表以外の行が来たらflushする
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_para()
            flush_list()
            flush_quote()
            table_buf.append(stripped)
            continue
        flush_table()

        if stripped.startswith("## "):
            flush_para()
            flush_list()
            flush_quote()
            html_parts.append(f"<h2>{inline_format(stripped[3:])}</h2>")
        elif stripped.startswith("### "):
            flush_para()
            flush_list()
            flush_quote()
            html_parts.append(f"<h3>{inline_format(stripped[4:])}</h3>")
        elif stripped.startswith("- "):
            flush_para()
            flush_quote()
            list_buf.append(stripped[2:])
        elif stripped.startswith("> "):
            flush_para()
            flush_list()
            blockquote_buf.append(stripped[2:])
        elif stripped.startswith("<"):
            # 生HTMLブロック（<figure> など）はそのまま素通しする
            flush_para()
            flush_list()
            flush_quote()
            html_parts.append(inline_format(stripped))
        elif stripped == "":
            flush_para()
            flush_list()
            flush_quote()
        else:
            flush_list()
            flush_quote()
            para_buf.append(stripped)

    flush_para()
    flush_list()
    flush_quote()
    flush_table()

    return "\n".join(html_parts)


# ---------- WP REST API ----------

def post_or_update(env: dict, fm: dict, html_body: str, media_only: bool = False):
    site = env["WP_SITE_URL"].rstrip("/")
    user = env["WP_USER"]
    app_pass = env["WP_APP_PASS"].replace(" ", "")
    post_type = env.get("WP_POST_TYPE", "posts")

    auth = base64.b64encode(f"{user}:{app_pass}".encode()).decode()

    wp_post_id = fm.get("wp_post_id")

    if media_only:
        # featured_media だけを差し替える。本文/タイトル/抜粋/カテゴリは触らない
        if not wp_post_id:
            sys.stderr.write(
                "--media-only は既存投稿を前提とします。フロントマターに wp_post_id がありません。\n"
            )
            sys.exit(1)
        if not fm.get("featured_media"):
            sys.stderr.write(
                "--media-only 実行中ですが featured_media が取得できませんでした。"
                "eyecatch_image のパスとファイル存在を確認してください。\n"
            )
            sys.exit(1)
        try:
            payload = {"featured_media": int(fm["featured_media"])}
        except (TypeError, ValueError):
            sys.stderr.write("featured_media の値が数値ではありません。\n")
            sys.exit(1)
        endpoint = f"{site}/wp-json/wp/v2/{post_type}/{wp_post_id}"
        mode = "update (media-only)"
    else:
        category_field = fm.get("category_field", "categories")
        category_id = int(fm["category_id"])

        payload = {
            "title": fm["title"],
            "content": html_body,
            "excerpt": fm.get("excerpt", ""),
            category_field: [category_id],
        }

        # パーマリンク（slug）。日本語を避けるため、フロントマターの英語slugを必ず送る
        if fm.get("slug"):
            payload["slug"] = fm["slug"]

        # アイキャッチ（featured_media）。process_media がフロントマターに付与する
        if fm.get("featured_media"):
            try:
                payload["featured_media"] = int(fm["featured_media"])
            except (TypeError, ValueError):
                pass

        if wp_post_id:
            endpoint = f"{site}/wp-json/wp/v2/{post_type}/{wp_post_id}"
            mode = "update"
        else:
            payload["status"] = "draft"
            endpoint = f"{site}/wp-json/wp/v2/{post_type}"
            mode = "create"

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read().decode())
            status = resp.status
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP {e.code} error:\n{e.read().decode()}\n")
        sys.exit(1)

    return mode, status, body


def append_post_id(md_path: Path, post_id: int):
    """新規作成成功時、フロントマターに wp_post_id を追記する。"""
    text = md_path.read_text(encoding="utf-8")
    if "wp_post_id:" in text:
        return
    # 'category_field: "..."' の行の直後に挿入
    new_lines = []
    inserted = False
    for line in text.splitlines():
        new_lines.append(line)
        if (not inserted) and line.startswith("category_field:"):
            new_lines.append(f"wp_post_id: {post_id}")
            inserted = True
    md_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


# ---------- メディア（挿絵・アイキャッチ）アップロード ----------

def upload_media(env: dict, path: Path):
    """画像を WP メディアライブラリへアップロードし (id, source_url) を返す。"""
    site = env["WP_SITE_URL"].rstrip("/")
    user = env["WP_USER"]
    app_pass = env["WP_APP_PASS"].replace(" ", "")
    auth = base64.b64encode(f"{user}:{app_pass}".encode()).decode()
    fname = path.name
    # Content-Disposition は latin-1 でエンコードされるため、日本語等の非ASCIIファイル名は
    # ASCIIへ変換してから送る（変換しないと UnicodeEncodeError でアップロードが落ちる）
    safe_fname = re.sub(r"[^A-Za-z0-9._-]", "-", fname).strip("-") or "image.png"
    mime, _ = mimetypes.guess_type(fname)
    data = path.read_bytes()
    req = urllib.request.Request(
        f"{site}/wp-json/wp/v2/media",
        data=data,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": mime or "image/png",
            "Content-Disposition": f'attachment; filename="{safe_fname}"',
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode())
    return body["id"], body["source_url"]


def process_media(env: dict, md_path: Path, md_text: str) -> str:
    """本文中の <img src="drafts/..."> をWPメディアへアップしてURLに置換し、
    フロントマターの eyecatch_image をアップして featured_media を付与する。
    変更は md_path に永続化し、再実行時の二重アップロードを防ぐ
    （次回はsrcがhttp URLになるため対象外になる）。"""
    repo_root = md_path.resolve().parent.parent
    changed = False

    # 1) 本文のローカル画像（挿絵・提唱者ポートレート等）
    local_srcs = sorted(set(re.findall(r'src="(drafts/[^"]+\.(?:png|jpe?g))"', md_text)))
    for src in local_srcs:
        img_path = (repo_root / src).resolve()
        if not img_path.exists():
            sys.stderr.write(f"[media] 見つからないのでスキップ: {src}\n")
            continue
        _id, url = upload_media(env, img_path)
        md_text = md_text.replace(f'src="{src}"', f'src="{url}"')
        changed = True
        print(f"[media] 挿絵アップロード: {src} -> {url}")

    # 2) アイキャッチ → featured_media
    fm, _ = parse_frontmatter(md_text)
    eyecatch = fm.get("eyecatch_image", "")
    if eyecatch.startswith("drafts/") and not fm.get("featured_media"):
        ec_path = (repo_root / eyecatch).resolve()
        if ec_path.exists():
            mid, _url = upload_media(env, ec_path)
            md_text = md_text.replace(
                "eyecatch_image:", f"featured_media: {mid}\neyecatch_image:", 1
            )
            changed = True
            print(f"[media] アイキャッチアップロード: featured_media={mid}")
        else:
            sys.stderr.write(f"[media] アイキャッチが見つからない: {eyecatch}\n")

    if changed:
        md_path.write_text(md_text, encoding="utf-8")
    return md_text


# ---------- main ----------

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    flags = [a for a in sys.argv[1:] if a.startswith("-")]
    media_only = "--media-only" in flags

    if len(args) < 1:
        sys.stderr.write(
            "usage: python3 scripts/post_to_wp.py drafts/{filename}.md [--media-only]\n"
        )
        sys.exit(2)

    repo_root = Path(__file__).resolve().parent.parent
    env_path = repo_root / ".env"
    if not env_path.exists():
        sys.stderr.write(f".env が見つかりません: {env_path}\n")
        sys.exit(1)
    env = load_env(env_path)

    md_arg = args[0]
    md_path = (repo_root / md_arg).resolve()
    if not md_path.exists():
        sys.stderr.write(f"MDファイルが見つかりません: {md_path}\n")
        sys.exit(1)

    md_text = md_path.read_text(encoding="utf-8")
    # 挿絵・アイキャッチをWPメディアへアップロードし、本文URLとfeatured_mediaを反映
    md_text = process_media(env, md_path, md_text)
    fm, body = parse_frontmatter(md_text)
    if not fm:
        sys.stderr.write("フロントマターが読み取れませんでした。\n")
        sys.exit(1)

    if media_only:
        html_body = ""  # --media-only では本文送信しないので空でよい
        print("==== --media-only モード（本文は上書きしません） ====\n")
    else:
        html_body = md_to_html(body)
        print(f"==== HTML プレビュー（先頭400字） ====\n{html_body[:400]}\n...\n")

    mode, status, resp_body = post_or_update(env, fm, html_body, media_only=media_only)
    post_id = resp_body.get("id")
    link = resp_body.get("link")
    site = env["WP_SITE_URL"].rstrip("/")
    edit_url = f"{site}/wp-admin/post.php?post={post_id}&action=edit"

    print(f"\n==== 結果 ====")
    print(f"モード        : {mode}")
    print(f"HTTP          : {status}")
    print(f"投稿ID        : {post_id}")
    print(f"WP編集URL     : {edit_url}")
    print(f"公開URL候補   : {link}")

    if mode == "create" and post_id:
        append_post_id(md_path, post_id)
        print(f"wp_post_id    : {post_id} をフロントマターに追記しました")


if __name__ == "__main__":
    main()
