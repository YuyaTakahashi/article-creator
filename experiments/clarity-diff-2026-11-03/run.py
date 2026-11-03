"""article-creator の出力に GPT で「わかりやすくして」をかけ、どこが変わるかを測る。
段階: T3=GPT turn3（執筆直後） / F=drafts の最終版（Critic・手直し後） / W=F に「わかりやすくして」をかけたもの
"""
import json, os, re, sys, difflib, urllib.request
sys.path.insert(0, 'scripts')
REPO = os.getcwd()
OUT = 'experiments/clarity-diff-2026-11-03'
TERMS = ['SQLインジェクション', 'GUI', 'ソフト・ラベリング']
env = {}
for l in open('.env'):
    if '=' in l and not l.startswith('#'):
        k, v = l.split('=', 1); env[k.strip()] = v.strip().strip('"\'')

def body(md):
    m = re.search(r'^.*wp\s*分割\s*ライン.*$', md, re.M)
    s = md[m.end():] if m else md
    s = re.split(r'^##\s*関連用語', s, flags=re.M)[0]
    return s.strip()

def chat(text):
    req = urllib.request.Request('https://api.openai.com/v1/chat/completions',
        data=json.dumps({'model': 'gpt-6.1-sol', 'messages': [{'role': 'user', 'content': 'わかりやすくして\n\n' + text}]}).encode(),
        headers={'Authorization': 'Bearer ' + env['OPENAI_API_KEY'], 'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=600))['choices'][0]['message']['content']

for t in TERMS:
    T3 = body(open(f'pipeline/gpt/{t}_turn3_gpt-6.1-sol.md').read())
    F = body(open(f'drafts/{t}.md').read())
    wp = f'{OUT}/{t}_W.md'
    if not os.path.exists(wp):
        open(wp, 'w').write(chat(F))
    W = open(wp).read().strip()
    open(f'{OUT}/{t}_T3.md', 'w').write(T3); open(f'{OUT}/{t}_F.md', 'w').write(F)
    print(t, 'chars T3/F/W', len(T3), len(F), len(W), flush=True)
