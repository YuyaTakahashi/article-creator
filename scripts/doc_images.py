#!/usr/bin/env python3
"""記事のアイキャッチ候補と挿絵をDocへ差し込む。

アイキャッチはClaudeがSVGで描き、ここでPNGにする。挿絵はOpenAIの画像モデル（gpt-image-2）で作る。

画像をWP下書きのあとで別工程（/glossary-wp-images）として入れていたころは、Claudeを持つ人しか
画像を作れず、WP下書きが画像なしのまま止まっていた。いまは生成バッチがDocまで画像を入れ、
レビューする人はDocで要らない画像を消すだけにする。残った画像は、用語くんがWP下書きにするときに
WPメディアへ上げる（アイキャッチは featured_media、挿絵は本文の <figure>）。

画像生成AI（Gemini）に描かせていたころは、日本語の文字化け・ラベルの重複・タイトル位置のずれで
作り直しが多かった。そこで画像の中の文字はすべてやめるか、SVGで入れる。
- アイキャッチ：タイトル文字が要るのでSVG。文字と配置をコードで決められるので、崩れない
- 挿絵：ClaudeのSVGでは図が粗く、絵として見られるものにならなかった。画像モデルに文字なしで描かせる

Docへの差し込みは用語くん（GAS）の webhook が行う。Doc化に使う Drive コネクタの create_file は
Markdownから作るので画像を入れられず、DocumentApp なら画像データをそのまま入れられるため。

使い方（Doc化の直後に、Macで実行する）:
    1. 挿絵の計画を drafts/{slug}-images.json に書く（prompt は英語。画像に文字を描かせない）:
         {"illustrations": [{"heading": "効果", "prompt": "<その章の本文の例を描く英語の説明>"}]}
       heading は Doc の ## 見出しの文字と同じにする。挿絵が要らなければ illustrations を空にする。
    2. アイキャッチのSVGを描く（1024×1024。書き方は style-guide-eyecatch.md）:
         drafts/{slug}-eyecatch-1.svg, drafts/{slug}-eyecatch-2.svg
    3. アイキャッチをPNGにする（Chrome のヘッドレスで描画する）:
         python3 scripts/doc_images.py render "drafts/{用語}.md"
    4. 挿絵を作る（.env の OPENAI_API_KEY を使う）。作り直したい挿絵だけ --only illust-2 のように指定できる:
         python3 scripts/doc_images.py generate "drafts/{用語}.md"
       できたPNGを Read で見て確かめ、だめなら prompt を直して --only で作り直す。
    4.5 挿絵に日本語のラベルを重ねる（画像生成AIに文字を描かせず、後からヒラギノで描く）:
         python3 scripts/doc_images.py label "drafts/{用語}.md"
       ラベルは images.json の各挿絵に "labels": [{"text": "見えない指示", "x": 0.05, "y": 0.67}] の形で書く。
       x・y は札の左上の位置で、画像の幅・高さに対する割合（0〜1）。生成した画像を Read で見て、
       指したい要素のすぐ近くで、要素に重ならない位置を選ぶ。label は生成直後の画像（*_raw.png）から
       毎回描き直すので、位置を直して何度実行してもラベルは重ならない。
    5. Docへ送る:
         python3 scripts/doc_images.py send "drafts/{用語}.md" --doc-url "<DocURL>"
       送る前にDocから前回入れた画像（アイキャッチ候補と挿絵）を消すので、何度送り直しても重ならない。
"""

import argparse
import base64
import io
import json
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_eyecatch import load_env, parse_frontmatter  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
EYECATCH_COUNT = 2   # 1案だと気に入らないときに作り直しの手間が戻るので、2案並べて選んでもらう
EYECATCH_SIZE = (1024, 1024)
OPENAI_MODEL = "gpt-image-2"
OPENAI_SIZE = "1536x1024"   # 横長。章の流れ図は横長のほうが収まる
OPENAI_QUALITY = "medium"   # 1枚あたり約0.05ドル（2026-10時点の公開情報）。high は約4倍

# 挿絵の絵柄。画像の中に文字を描かせない（Geminiで日本語ラベルが崩れ、作り直しの主な原因だったため）
ILLUST_PROMPT_TEMPLATE = """A clean editorial explainer illustration for a Japanese UX glossary article, landscape composition.

STYLE:
- Solid white background, generous whitespace, one clear focal scene in the center
- Flat vector illustration with simple shapes and thin, even dark-gray outlines
- Calm palette: soft blue as the main color, with small accents of warm yellow and soft coral; no gradients, no 3D, no photorealism, no heavy shadows
- Neutral, adult, design-magazine tone. Simple faceless or minimal-face people are fine; no mascots, no big-eyed cute characters
- Show the idea through concrete, recognizable objects and their spatial relationship, so the point is clear without any words

TEXT: Absolutely no text, letters, numbers, labels, logos, or watermarks anywhere in the image.

SCENE:
{scene}"""
MAX_SIDE = 1600      # Docとwebhookを重くしないための長辺の上限
# 挿絵のラベル。画像生成AIに日本語を描かせると崩れるので、生成後にヒラギノで重ねる
LABEL_FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
LABEL_INK = (26, 26, 26)
LABEL_BORDER = (201, 163, 94)   # アイキャッチと同じマスタード
LABEL_MAX_CHARS = 12            # 札は短い名詞句にする。長い説明は本文に書く
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def plan_path(md_path: Path, slug: str) -> Path:
    return md_path.parent / f"{slug}-images.json"


def build_jobs(md_path: Path):
    """扱う画像の一覧を返す。[{key, kind, heading, svg, file, size}]"""
    fm = parse_frontmatter(md_path.read_text(encoding="utf-8"))
    slug = fm.get("slug") or md_path.stem
    jobs = []
    for n in range(1, EYECATCH_COUNT + 1):
        jobs.append({"key": f"eyecatch-{n}", "kind": "eyecatch", "heading": "",
                     "svg": f"drafts/{slug}-eyecatch-{n}.svg", "file": f"drafts/{slug}-eyecatch-{n}.png",
                     "size": EYECATCH_SIZE})
    plan_file = plan_path(md_path, slug)
    plan = json.loads(plan_file.read_text(encoding="utf-8")) if plan_file.exists() else {}
    if not plan_file.exists():
        print(f"[images] {plan_file.relative_to(BASE)} が無いので、挿絵は扱わない")
    for n, it in enumerate(plan.get("illustrations", []), start=1):
        if not it.get("heading"):
            sys.exit(f"{plan_file.name} の {n} 件目に heading がありません")
        jobs.append({"key": f"illust-{n}", "kind": "illustration", "heading": it["heading"].strip(),
                     "prompt": (it.get("prompt") or "").strip(), "file": f"drafts/{slug}_{n}.png",
                     "raw": f"drafts/{slug}_{n}_raw.png", "labels": it.get("labels") or []})
    return fm, jobs


def render_svg(svg: Path, png: Path, size):
    """SVGをChromeのヘッドレスで開いてPNGに書き出す。日本語はMacのフォント（ヒラギノ）で描かれる。"""
    w, h = size
    with tempfile.TemporaryDirectory() as tmp:
        # SVGを直接開くと余白や拡大率がぶれるので、原寸で置いたHTMLを撮る
        html = Path(tmp) / "page.html"
        html.write_text(
            '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;padding:0;overflow:hidden}'
            f'img{{display:block;width:{w}px;height:{h}px}}</style><img src="{svg.resolve().as_uri()}">',
            encoding="utf-8")
        out = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
             "--allow-file-access-from-files", f"--window-size={w},{h}", f"--screenshot={png}", html.as_uri()],
            capture_output=True, text=True, timeout=60)
    if not png.exists():
        raise RuntimeError(out.stderr.strip()[-300:] or "PNGが書き出されなかった")


def render(md_path: Path):
    if not Path(CHROME).exists():
        sys.exit(f"Chrome が見つかりません: {CHROME}")
    _, jobs = build_jobs(md_path)
    done = missing = failed = 0
    for j in [j for j in jobs if j["kind"] == "eyecatch"]:
        svg, png = BASE / j["svg"], BASE / j["file"]
        where = f"（{j['heading']}）" if j["heading"] else ""
        if not svg.exists():
            missing += 1
            print(f"  skip {j['key']}{where}: {j['svg']} が無い")
            continue
        if png.exists():
            png.unlink()
        try:
            render_svg(svg, png, j["size"])
        except Exception as e:
            failed += 1
            print(f"  NG {j['key']}{where}: {e}")
            continue
        done += 1
        print(f"  ok {j['key']}{where} → {j['file']}")
    print(f"[images] PNGにした {done} 枚 / SVGが無い {missing} 枚 / 失敗 {failed} 枚")
    return 1 if failed or not done else 0


def call_openai_image(api_key: str, prompt: str) -> bytes:
    """OpenAIの画像モデルで1枚作り、PNGのバイト列を返す。失敗したら RuntimeError。"""
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=json.dumps({"model": OPENAI_MODEL, "prompt": prompt, "size": OPENAI_SIZE,
                         "quality": OPENAI_QUALITY, "n": 1}).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        body = json.loads(urllib.request.urlopen(req, timeout=300).read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        try:
            detail = json.loads(detail)["error"]["message"]
        except Exception:
            detail = detail[:300]
        raise RuntimeError(f"OpenAI {e.code}: {detail}")
    data = (body.get("data") or [{}])[0]
    if not data.get("b64_json"):
        raise RuntimeError(f"画像が返らなかった: {json.dumps(body)[:300]}")
    return base64.b64decode(data["b64_json"])


def generate(md_path: Path, only):
    env = load_env(BASE / ".env")
    api_key = env.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("OPENAI_API_KEY が .env に設定されていません。")
    _, jobs = build_jobs(md_path)
    jobs = [j for j in jobs if j["kind"] == "illustration"]
    if only:
        unknown = set(only) - {j["key"] for j in jobs}
        if unknown:
            sys.exit(f"--only に知らないキーがあります: {', '.join(sorted(unknown))}")
        jobs = [j for j in jobs if j["key"] in only]
    for j in jobs:
        if not j["prompt"]:
            sys.exit(f"{j['key']}（{j['heading']}）に prompt がありません")
    if not jobs:
        print("[images] 作る挿絵がありません")
        return 0

    def run(job):
        try:
            data = call_openai_image(api_key, ILLUST_PROMPT_TEMPLATE.format(scene=job["prompt"]))
        except Exception as e:
            return job, str(e)
        (BASE / job["file"]).write_bytes(data)
        (BASE / job["raw"]).write_bytes(data)   # label はここから描き直す
        return job, ""

    # 1枚に数十秒かかるので並列に走らせる
    print(f"[images] 挿絵 {len(jobs)} 枚を生成中（{OPENAI_MODEL} / {OPENAI_QUALITY}）…")
    failed = 0
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        for job, err in ex.map(run, jobs):
            if err:
                failed += 1
                print(f"  NG {job['key']}（{job['heading']}）: {err}")
            else:
                print(f"  ok {job['key']}（{job['heading']}） → {job['file']}")
    return 1 if failed == len(jobs) else 0


def draw_labels(raw: Path, out: Path, labels):
    """raw の画像に札（白地・マスタードの枠・黒字）を重ねて out に書き出す。"""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(raw).convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img)
    size = max(20, round(W * 0.022))
    pad = round(size * 0.45)
    font = ImageFont.truetype(LABEL_FONT, size)
    for lb in labels:
        text = str(lb["text"]).strip()
        if len(text) > LABEL_MAX_CHARS:
            print(f"  注意: ラベル「{text}」が{LABEL_MAX_CHARS}文字を超えている。短くする")
        w = d.textlength(text, font=font)
        bw, bh = w + pad * 2, size + pad * 2
        x = min(max(0, float(lb["x"]) * W), W - bw)
        y = min(max(0, float(lb["y"]) * H), H - bh)
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=round(size * 0.4),
                            fill="white", outline=LABEL_BORDER, width=max(3, round(size * 0.11)))
        d.text((x + pad, y + pad - round(size * 0.06)), text, font=font, fill=LABEL_INK)
    img.save(out)


def label(md_path: Path, only):
    try:
        import PIL  # noqa: F401
    except ImportError:
        sys.exit("Pillow が必要です: python3 -m pip install Pillow")
    if not Path(LABEL_FONT).exists():
        sys.exit(f"フォントが見つかりません: {LABEL_FONT}")
    _, jobs = build_jobs(md_path)
    jobs = [j for j in jobs if j["kind"] == "illustration" and (not only or j["key"] in only)]
    done = 0
    for j in jobs:
        f, raw = BASE / j["file"], BASE / j["raw"]
        if not f.exists():
            print(f"  skip {j['key']}: {j['file']} が無い（先に generate）")
            continue
        if not raw.exists():
            raw.write_bytes(f.read_bytes())   # 旧い記事は今の画像を生成直後の画像とみなす
        if not j["labels"]:
            f.write_bytes(raw.read_bytes())
            print(f"  ok {j['key']}（{j['heading']}）: ラベルなし")
            continue
        draw_labels(raw, f, j["labels"])
        done += 1
        print(f"  ok {j['key']}（{j['heading']}）: ラベル {len(j['labels'])} 個")
    print(f"[images] ラベルを重ねた挿絵 {done} 枚")
    return 0


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
            print(f"  skip {j['key']}: {j['file']} が無い（render / generate で作るか、計画から外す）")
    if not ready:
        sys.exit("送る画像がありません。先に render / generate を実行してください。")

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
    r = sub.add_parser("render", help="アイキャッチのSVGをPNGにする")
    r.add_argument("md_path")
    g = sub.add_parser("generate", help="挿絵をOpenAIで作る")
    g.add_argument("md_path")
    g.add_argument("--only", action="append", default=[],
                   help="作り直す挿絵のキー（illust-1 など）。複数指定できる")
    lb = sub.add_parser("label", help="挿絵に日本語のラベルを重ねる")
    lb.add_argument("md_path")
    lb.add_argument("--only", action="append", default=[],
                    help="ラベルを描き直す挿絵のキー（illust-1 など）。複数指定できる")
    s = sub.add_parser("send", help="drafts/ の画像をDocへ差し込む")
    s.add_argument("md_path")
    s.add_argument("--doc-url", required=True)
    s.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    md_path = (BASE / args.md_path).resolve()
    if not md_path.exists():
        sys.exit(f"MDファイルが見つかりません: {md_path}")
    if args.cmd == "render":
        sys.exit(render(md_path))
    if args.cmd == "generate":
        sys.exit(generate(md_path, args.only))
    if args.cmd == "label":
        sys.exit(label(md_path, args.only))
    sys.exit(send(md_path, args.doc_url, args.dry_run))


if __name__ == "__main__":
    main()
