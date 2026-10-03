#!/usr/bin/env python3
"""記事のアイキャッチ候補と挿絵を生成し、レビュー用のGoogleドキュメントへ差し込む。

画像をWP下書きのあとで別工程（/glossary-wp-images）として入れていたころは、Claudeを持つ人しか
画像を作れず、WP下書きが画像なしのまま止まっていた。いまは生成バッチがDocまで画像を入れ、
レビューする人はDocで要らない画像を消すだけにする。残った画像は、用語くんがWP下書きにするときに
WPメディアへ上げる（アイキャッチは featured_media、挿絵は本文の <figure>）。

Docへの差し込みは用語くん（GAS）の webhook が行う。Doc化に使う Drive コネクタの create_file は
Markdownから作るので画像を入れられず、DocumentApp なら画像データをそのまま入れられるため。

使い方（Doc化の直後に、Macで実行する）:
    1. 挿絵の計画を drafts/{slug}-images.json に書く（Claudeが本文を読んで書く）:
         {"illustrations": [{"heading": "効果", "prompt": "<英語メタファー＋描いてよい日本語ラベル>"}]}
       heading は Doc の ## 見出しの文字と同じにする。挿絵が要らなければ illustrations を空にする。
    2. 生成する（画像は drafts/ に保存される。まだDocには入れない）:
         python3 scripts/doc_images.py generate "drafts/{用語}.md"
       作り直したい画像だけ --only で指定できる（例: --only eyecatch-2 --only illust-1）。
    3. 生成した画像を目で確かめたら、Docへ送る:
         python3 scripts/doc_images.py send "drafts/{用語}.md" --doc-url "<DocURL>"
       送る前にDocから前回入れた画像（アイキャッチ候補と挿絵）を消すので、何度送り直しても重ならない。
"""

import argparse
import base64
import io
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_eyecatch import build_prompt, call_gemini_image, load_env, parse_frontmatter  # noqa: E402
from generate_illustration import SECTION_PROMPT_TEMPLATE  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
EYECATCH_COUNT = 2   # 1案だと気に入らないときに作り直しの手間が戻るので、2案並べて選んでもらう
MAX_SIDE = 1600      # Docとwebhookを重くしないための長辺の上限


def plan_path(md_path: Path, slug: str) -> Path:
    return md_path.parent / f"{slug}-images.json"


def build_jobs(md_path: Path):
    """生成する画像の一覧を返す。[{key, kind, heading, prompt, file}]"""
    fm = parse_frontmatter(md_path.read_text(encoding="utf-8"))
    slug = fm.get("slug") or md_path.stem
    jobs = []
    eyecatch_prompt = build_prompt(fm, md_path.stem)
    if eyecatch_prompt:
        for n in range(1, EYECATCH_COUNT + 1):
            jobs.append({"key": f"eyecatch-{n}", "kind": "eyecatch", "heading": "",
                         "prompt": eyecatch_prompt, "file": f"drafts/{slug}-eyecatch-{n}.png"})
    else:
        print("[images] フロントマターに eyecatch_prompt が無いので、アイキャッチは作らない")

    plan_file = plan_path(md_path, slug)
    plan = json.loads(plan_file.read_text(encoding="utf-8")) if plan_file.exists() else {}
    if not plan_file.exists():
        print(f"[images] {plan_file.relative_to(BASE)} が無いので、挿絵は作らない")
    for n, it in enumerate(plan.get("illustrations", []), start=1):
        if not it.get("heading") or not it.get("prompt"):
            sys.exit(f"{plan_file.name} の {n} 件目に heading か prompt がありません")
        jobs.append({"key": f"illust-{n}", "kind": "illustration", "heading": it["heading"].strip(),
                     "prompt": SECTION_PROMPT_TEMPLATE.format(metaphor=it["prompt"].strip()),
                     "file": f"drafts/{slug}_{n}.png"})
    return fm, jobs


def generate(md_path: Path, only):
    env = load_env(BASE / ".env")
    api_key = env.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY が .env に設定されていません。")
    _, jobs = build_jobs(md_path)
    if only:
        unknown = set(only) - {j["key"] for j in jobs}
        if unknown:
            sys.exit(f"--only に知らないキーがあります: {', '.join(sorted(unknown))}")
        jobs = [j for j in jobs if j["key"] in only]
    if not jobs:
        print("[images] 作る画像がありません")
        return 0

    def run(job):
        try:
            data = call_gemini_image(api_key, job["prompt"])
        except BaseException as e:  # call_gemini_image は失敗時に sys.exit するので SystemExit も受ける
            return job, f"生成に失敗（{e}）"
        (BASE / job["file"]).write_bytes(data)
        return job, ""

    # 画像生成は1枚に数十秒かかるので並列に走らせる
    print(f"[images] {len(jobs)} 枚を生成中…")
    failed = 0
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        for job, err in ex.map(run, jobs):
            where = f"（{job['heading']}）" if job["heading"] else ""
            if err:
                failed += 1
                print(f"  NG {job['key']}{where}: {err}")
            else:
                print(f"  ok {job['key']}{where} → {job['file']}")
    return 1 if failed == len(jobs) else 0


def shrink(path: Path):
    """長辺を MAX_SIDE までに縮め、(base64, mime) を返す。Pillow が無ければそのまま送る。"""
    raw = path.read_bytes()
    try:
        from PIL import Image
    except ImportError:
        return base64.b64encode(raw).decode(), "image/png"
    img = Image.open(io.BytesIO(raw))
    if max(img.size) <= MAX_SIDE:
        return base64.b64encode(raw).decode(), "image/png"
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode(), "image/png"


def post(env, payload):
    req = urllib.request.Request(env["GAS_WEBAPP_URL"],
                                 data=json.dumps(dict(payload, token=env["GAS_TOKEN"])).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read().decode("utf-8"))


def send(md_path: Path, doc_url: str, dry_run: bool):
    env = load_env(BASE / ".env")
    for k in ("GAS_WEBAPP_URL", "GAS_TOKEN"):
        if not env.get(k):
            sys.exit(f"{k} が .env に設定されていません。")
    fm, jobs = build_jobs(md_path)
    title = fm.get("title") or md_path.stem
    ready = [j for j in jobs if (BASE / j["file"]).exists()]
    for j in jobs:
        if j not in ready:
            print(f"  skip {j['key']}: {j['file']} が無い（generate で作り直すか、計画から外す）")
    if not ready:
        sys.exit("送る画像がありません。先に generate を実行してください。")

    if dry_run:
        for j in ready:
            print(f"  [dry-run] {j['kind']} {j['heading'] or ''} ← {j['file']}")
        return 0

    res = post(env, {"action": "clear_doc_images", "doc_url": doc_url})
    if not res.get("ok"):
        sys.exit(f"Docの前回の画像を消せませんでした: {res}")
    if res.get("removed"):
        print(f"[images] Docから前回の画像を {res['removed']} 枚消した")

    failed = 0
    for j in ready:
        data, mime = shrink(BASE / j["file"])
        alt = f"{title}のアイキャッチ" if j["kind"] == "eyecatch" else f"{j['heading']}のイメージ"
        res = post(env, {"action": "insert_doc_image", "doc_url": doc_url, "kind": j["kind"],
                         "heading": j["heading"], "alt": alt, "mime": mime,
                         "name": Path(j["file"]).name, "data": data})
        where = f"（{j['heading']}）" if j["heading"] else ""
        if res.get("ok"):
            print(f"  ok {j['key']}{where} をDocに入れた")
        else:
            failed += 1
            print(f"  NG {j['key']}{where}: {res.get('error')}")
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser(description="アイキャッチ候補と挿絵を生成し、レビュー用Docへ差し込む")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="画像を生成して drafts/ に保存する")
    g.add_argument("md_path")
    g.add_argument("--only", action="append", default=[],
                   help="作り直す画像のキー（eyecatch-1, illust-2 など）。複数指定できる")
    s = sub.add_parser("send", help="drafts/ の画像をDocへ差し込む")
    s.add_argument("md_path")
    s.add_argument("--doc-url", required=True)
    s.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    md_path = (BASE / args.md_path).resolve()
    if not md_path.exists():
        sys.exit(f"MDファイルが見つかりません: {md_path}")
    if args.cmd == "generate":
        sys.exit(generate(md_path, args.only))
    sys.exit(send(md_path, args.doc_url, args.dry_run))


if __name__ == "__main__":
    main()
