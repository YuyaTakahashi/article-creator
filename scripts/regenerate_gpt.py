#!/usr/bin/env python3
"""既存の用語記事を GPT で書き直し、Doc の作り直しと用語DBの書き戻しまでを1回で行う。

GPT で書き直しても Doc を作り直さないと、レビューする Doc と drafts/ の中身がずれる。
手で1工程ずつ回すと、Doc化・挿絵の差し込み・用語DBの書き戻し・Critic のどれかが抜けるので、
作り直しの工程をここにまとめる。

前提: research/{用語}_claims.md と _conditions.md があり、drafts/{用語}.md が前の版として残っている。
使い方:
    python3 scripts/regenerate_gpt.py "勾配消失・勾配爆発"
    python3 scripts/regenerate_gpt.py "勾配消失・勾配爆発" --id G-094     行を明示する
    python3 scripts/regenerate_gpt.py "勾配消失・勾配爆発" --skip-gpt     pipeline/gpt の既存 turn3 を使う
    python3 scripts/regenerate_gpt.py "勾配消失・勾配爆発" --skip-critic

工程:
  1. 用語DBで行を特定し、前の版の Doc URL とレシピ版を控える
  2. gpt_write.py で turn1〜turn3 を作る
  3. turn3 を drafts/{用語}.md の本文にし、フロントマター（excerpt・english・writer_model 等）を更新する
  4. 挿絵の計画（drafts/{slug}-images.json）の見出しを、新しい本文の同じ位置の見出しに付け替える
  5. stamp_version.py でレシピ版を刻む
  6. article-critic を claude -p で通す（判定はログに残し、Doc化は止めない）
  7. make_doc_md.py → Drive にMDを上げて Google ドキュメントに変換 → 元のMDはゴミ箱へ
  8. doc_images.py send で、アイキャッチ候補と挿絵を新しい Doc に入れる
  9. register_draft.py --id で用語DBを書き戻す（作り直しメモと旧Docリンク付き）
"""
import argparse, json, os, re, subprocess, sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from register_draft import read_sheet, find_row, read_frontmatter  # noqa: E402

DOC_FOLDER = "1tQU3-ts3mU6YusLFjijNDNGzdcf-y-GS"
COL_DOC, COL_VERSION = 8, 18  # 用語DBの I列（記事Doc）、S列（生成バージョン）


def run(cmd, check=True):
    print("$ " + " ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=REPO, text=True, capture_output=True)
    out = (r.stdout or "") + (r.stderr or "")
    print(out.rstrip())
    if check and r.returncode != 0:
        sys.exit(f"失敗: {' '.join(cmd[:3])}")
    return out


def gws(args):
    r = subprocess.run(["gws"] + args, cwd=REPO, text=True, capture_output=True)
    body = r.stdout[r.stdout.find("{"):] if "{" in r.stdout else ""
    data = json.loads(body) if body else {}
    if r.returncode != 0 or "error" in data:
        sys.exit(f"gws {' '.join(args[:3])} に失敗: {data or r.stderr[:300]}")
    return data


def body_h2(text):
    """本文の ## 見出し（最小限の説明・関連用語を除く）を上から順に返す"""
    return [h.strip() for h in re.findall(r"^## (.+)$", text, re.M)
            if h.strip() not in ("最小限の説明", "関連用語", "記事タイトル")]


def set_fm(fm, key, value):
    line = f'{key}: "{value}"'
    if re.search(rf"^{key}:", fm, re.M):
        return re.sub(rf"^{key}:.*$", lambda _: line, fm, flags=re.M)
    return fm.rstrip("\n") + "\n" + line + "\n"


def apply_turn3(md_path, turn3_text, model, english):
    src = md_path.read_text(encoding="utf-8")
    _, fm, _ = src.split("---\n", 2)
    if "## 最小限の説明" not in turn3_text:
        sys.exit("turn3 に「## 最小限の説明」が無い。GPTの出力を確かめる")
    body = turn3_text[turn3_text.index("## 最小限の説明"):].rstrip() + "\n"
    body = re.sub(r"^## 最小限の説明\n+", "## 最小限の説明\n\n", body, flags=re.M)
    mini = body.split("\n\n")[1].strip()
    fm = set_fm(fm, "excerpt", mini)
    fm = set_fm(fm, "writer_model", model)
    fm = set_fm(fm, "polished_by", "regenerate_gpt.py（gpt_write.py turn3：読み手目線の書き直し）")
    fm = set_fm(fm, "generated_at", date.today().isoformat())
    if english:
        fm = set_fm(fm, "english", english)
    md_path.write_text("---\n" + fm + "---\n\n" + body, encoding="utf-8")
    return mini


def remap_images(plan_path, old_h2, new_h2):
    """挿絵の見出しを、新しい本文の同じ位置の見出しに付け替える。
    gpt_write.py の turn3 は見出しの数と順番を変えないので、位置で対応がとれる。"""
    if not plan_path.exists():
        print(f"挿絵の計画が無い（{plan_path.name}）。アイキャッチだけを入れる")
        return
    if len(old_h2) != len(new_h2):
        print(f"警告: 見出しの数が変わった（{len(old_h2)}→{len(new_h2)}）。挿絵の位置はDocで確かめる")
        return
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    for it in plan.get("illustrations", []):
        h = it.get("heading", "").strip()
        if h in old_h2:
            it["heading"] = new_h2[old_h2.index(h)]
            it["after"] = ""  # 段落の書き出しも書き直されているので、見出しの直後に置く
            print(f"  挿絵: {h} → {it['heading']}")
        elif h not in new_h2:
            print(f"警告: 挿絵の見出し「{h}」が旧本文にも新本文にも無い")
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")


def run_critic(topic, difficulty, it, attempt=1):
    prompt = (f"article-critic スキルで drafts/{topic}.md を評価する。作業ディレクトリは {REPO}。"
              f"article_type=ux_glossary, topic={topic}, difficulty={difficulty}, it={it}, attempt_count={attempt}, "
              "caller=regenerate_gpt.py。記事は書き直さない。ログJSONはスキルの規定の場所に保存する。"
              "出力の最後の1行は次の形にする: "
              "CRITIC: verdict=<pass|regenerate|escalate> template=<n> style=<n> reader=<n> readability=<n> log=<ログのパス>")
    print("$ claude -p （article-critic）", flush=True)
    try:
        r = subprocess.run(["claude", "-p", prompt, "--dangerously-skip-permissions"],
                           cwd=REPO, text=True, capture_output=True, timeout=1200,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "CRITIC: 20分で終わらなかった。あとで article-critic を手で通す"
    lines = [l for l in r.stdout.splitlines() if l.startswith("CRITIC:")]
    if lines:
        return lines[-1]
    # 認証切れ（Failed to authenticate）などで claude が動かなかったときは、その理由を見せる
    tail = " / ".join(((r.stderr or "") + (r.stdout or "")).strip().splitlines()[-2:])
    return f"CRITIC: 判定行を読めなかった（{tail[:200]}）。article-critic を手で通す"


MAX_FIX = 2          # 直しは2回まで（3回目の評価で残った指摘は人間に上げる）
MAX_CHANGE = 0.35    # 1回の直しで本文の35%を超える行が変わったら、部分修正の範囲を超えたとみなして採らない
CRITIC_LOG_DIR = Path.home() / "workspace/agentic-solution/AGENT_REPORTS/article-critic-logs"


def parse_critic(line, slug):
    """CRITIC 行とログJSONから、判定・4軸の合計・直す指摘を取り出す。読めなければ None"""
    if "verdict=" not in line:
        return None
    m = re.search(r"log=(\S+)", line)
    log = Path(os.path.expanduser(m.group(1))) if m else None
    if not log or not log.exists():
        cands = sorted((CRITIC_LOG_DIR / date.today().isoformat()).glob(f"{slug}_*.json"))
        log = cands[-1] if cands else None
    if not log:
        return None
    d = json.loads(log.read_text(encoding="utf-8"))
    totals = {k: v.get("total", 0) for k, v in d.get("scores", {}).items()}
    return {"verdict": d.get("verdict", ""), "totals": totals, "sum": sum(totals.values()),
            "points": d.get("regenerate_points", []), "log": str(log)}


FIX_PROMPT = """あなたはUX TIMES用語集の編集者です。下の[記事]に対して、[直す指摘]に挙がった箇所だけを直してください。

- 指摘に関係しない文は、一字も変えない。見出しの数・順番・文言も変えない
- 事実は足さない。言い換え・前提・計算例・たとえが必要なときは、[出典台帳]の（前提）（働き）（手計算）（たとえ）（結果）の材料を使う
- 指摘を直すために別の箇所を崩さない（同じ内容を2回書かない、本文を体言止めにしない、主語を消さない）
- 「## 最小限の説明」の本文を直したときは、20〜35文字に収め、「〜する現象」「〜する手法」のように名詞で終わる定義の形を保つ（ここだけは名詞で終える。句点は付けない）

前置きは不要です。直した記事全体（「## 最小限の説明」から「## 関連用語」まで）だけを出力してください。

### [直す指摘]
{points}

### [記事]
{article}

### [出典台帳]
{claims}
"""


def fix_with_gpt(topic, md_path, points, model):
    """Critic の指摘を GPT に部分修正させ、drafts に戻す。変えすぎた直しは採らず False を返す"""
    import difflib
    from gpt_write import chat, load_env
    load_env()
    src = md_path.read_text(encoding="utf-8")
    body = src[src.index("## 最小限の説明"):]
    claims = (REPO / f"research/{topic}_claims.md").read_text(encoding="utf-8")
    out = chat(model, [{"role": "user", "content": FIX_PROMPT.format(
        points="\n".join(f"- {x}" for x in points), article=body, claims=claims)}])
    if "## 最小限の説明" not in out:
        print("警告: 直しの出力に「## 最小限の説明」が無い。採らない")
        return False
    new_body = out[out.index("## 最小限の説明"):]
    a, b = body.splitlines(), new_body.splitlines()
    changed = 1 - difflib.SequenceMatcher(None, a, b).ratio()
    print(f"  直しで変わった行の割合: {changed:.0%}")
    if changed > MAX_CHANGE:
        print(f"警告: 変わった行が {MAX_CHANGE:.0%} を超えた。部分修正ではないので採らない")
        return False
    # 見出しの文言は直してよい（Critic が見出しを指摘することがある）。数と固定の見出しの位置だけを守る
    ob, nb = body_h2(body), body_h2(new_body)
    if len(ob) != len(nb) or [h == "語源・提唱者" for h in ob] != [h == "語源・提唱者" for h in nb]:
        print("警告: 直しで見出しの数か並びが変わった。採らない")
        return False
    apply_turn3(md_path, new_body, model, "")
    return True


def critic_loop(topic, md_path, slug, model, difficulty, it):
    """Critic → 指摘を部分修正 → 再評価を、指摘が無くなるまで回す。
    止まる条件: 指摘が無い ／ 直しを MAX_FIX 回した ／ 点数が上がらなかった ／ 直しを採れなかった"""
    best_text, best_sum, history = md_path.read_text(encoding="utf-8"), -1, []
    for attempt in range(1, MAX_FIX + 2):
        line = run_critic(topic, difficulty, it, attempt)
        print(line)
        r = parse_critic(line, slug)
        if r is None:
            return f"{line}（ループは止めた）"
        history.append(f"{attempt}回目 {r['verdict']} {r['totals']}")
        if r["sum"] <= best_sum:
            md_path.write_text(best_text, encoding="utf-8")
            return f"点数が上がらなかったので、前の版に戻して止めた（{' → '.join(history)}）。残る指摘: {r['points']}"
        best_text, best_sum = md_path.read_text(encoding="utf-8"), r["sum"]
        if not r["points"]:
            return f"指摘なしで止めた（{' → '.join(history)}）"
        if attempt > MAX_FIX:
            return f"直しを{MAX_FIX}回しても指摘が残った。要人間判断（{' → '.join(history)}）。残る指摘: {r['points']}"
        print(f"直し {attempt}回目: 指摘 {len(r['points'])} 件")
        if not fix_with_gpt(topic, md_path, r["points"], model):
            return f"直しを採れなかったので止めた（{' → '.join(history)}）。残る指摘: {r['points']}"
        run(["python3", "scripts/stamp_version.py", str(md_path)])
    return "想定外の終わり方"


def create_doc(topic, doc_md):
    """MDを Drive に上げ、コピー時に Google ドキュメントへ変換する。元のMDはゴミ箱へ送る。
    gws の files create は、アップロードと同時の変換を受け付けない（400）ため2段で行う。"""
    up = gws(["drive", "files", "create", "--params", '{"fields":"id"}',
              "--json", json.dumps({"name": f"{topic}.md", "parents": [DOC_FOLDER]}),
              "--upload", str(doc_md)])
    doc = gws(["drive", "files", "copy", "--params", json.dumps({"fileId": up["id"], "fields": "id"}),
               "--json", json.dumps({"name": topic, "mimeType": "application/vnd.google-apps.document",
                                     "parents": [DOC_FOLDER]}, ensure_ascii=False)])
    gws(["drive", "files", "update", "--params", json.dumps({"fileId": up["id"], "fields": "trashed"}),
         "--json", '{"trashed":true}'])
    return f"https://docs.google.com/document/d/{doc['id']}/edit"


def main():
    ap = argparse.ArgumentParser(description="GPTで書き直し、Doc作り直しと用語DB書き戻しまで行う")
    ap.add_argument("topic")
    ap.add_argument("--id", help="用語DBのG-ID（照合できないときに指定する）")
    ap.add_argument("--model", default="gpt-6.1-sol")
    ap.add_argument("--difficulty", default="0.3")
    ap.add_argument("--it", default="0.3")
    ap.add_argument("--skip-gpt", action="store_true", help="pipeline/gpt にある既存の turn3 を使う")
    ap.add_argument("--skip-critic", action="store_true")
    a = ap.parse_args()

    md = REPO / f"drafts/{a.topic}.md"
    if not md.exists():
        sys.exit(f"前の版が無い: {md}（新規の用語は generate-term.sh を使う）")

    # 1. 用語DBの行と前の版
    rows = read_sheet()
    if a.id:
        hit = [r for r in rows[1:] if r and str(r[0]).strip() == a.id]
        if not hit:
            sys.exit(f"用語DBに {a.id} が無い")
        gid, row = a.id, hit[0]
    else:
        _, gid, row = find_row(rows, a.topic)
        if not gid:
            sys.exit(f"用語DBに「{a.topic}」の行が見つからない。--id G-xxx で指定する")
    old_doc = row[COL_DOC].strip() if len(row) > COL_DOC else ""
    old_ver = (row[COL_VERSION].strip() if len(row) > COL_VERSION else "") \
        or read_frontmatter(md).get("creator_version", "") or "不明"
    print(f"用語DB: {gid} / 前の版 {old_ver} / 旧Doc {old_doc or '（なし）'}")
    old_h2 = body_h2(md.read_text(encoding="utf-8"))
    slug = read_frontmatter(md).get("slug", "")

    # 2. GPTで書き直す
    if not a.skip_gpt:
        run(["python3", "scripts/gpt_write.py", a.topic, "--model", a.model,
             "--difficulty", a.difficulty, "--it", a.it])
    turn3 = REPO / f"pipeline/gpt/{a.topic}_turn3_{a.model}.md"
    meta_p = REPO / f"pipeline/gpt/{a.topic}_meta.json"
    if not turn3.exists():
        sys.exit(f"turn3 が無い: {turn3}")
    english = json.loads(meta_p.read_text()).get("english", "") if meta_p.exists() else ""

    # 3〜5. drafts に反映し、挿絵の見出しを付け替え、版を刻む
    mini = apply_turn3(md, turn3.read_text(encoding="utf-8"), a.model, english)
    print(f"drafts を更新した（最小限の説明: {mini}）")
    run(["python3", "scripts/stamp_version.py", str(md.relative_to(REPO))])

    # 6. Critic → 指摘の部分修正 → 再評価のループ（結果に関わらず Doc化は止めない）
    critic = "CRITIC: 省略（--skip-critic）" if a.skip_critic else \
        critic_loop(a.topic, md, slug, a.model, a.difficulty, a.it)
    print(critic)
    # 挿絵の見出しは、ループで見出しの文言が変わったあとの本文に合わせる（数と順番は変わらない）
    remap_images(REPO / f"drafts/{slug}-images.json", old_h2, body_h2(md.read_text(encoding="utf-8")))

    # 7〜9. Doc を作り直し、画像を入れ、用語DBに書き戻す
    mk = ["python3", "scripts/make_doc_md.py", str(md.relative_to(REPO))]
    if old_doc:
        mk += ["--old-doc-url", old_doc]
    run(mk)
    doc_url = create_doc(a.topic, REPO / f"pipeline/doc-ready/{a.topic}.md")
    print(f"Docを作った: {doc_url}")
    run(["python3", "scripts/doc_images.py", "send", str(md.relative_to(REPO)), "--doc-url", doc_url],
        check=False)
    reg = ["python3", "scripts/register_draft.py", str(md.relative_to(REPO)), "--id", gid,
           "--doc-url", doc_url, "--regenerated-from", old_ver]
    if old_doc:
        reg += ["--old-doc-url", old_doc]
    run(reg)

    print(f"\n完了: {gid} / {doc_url}\n{critic}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
