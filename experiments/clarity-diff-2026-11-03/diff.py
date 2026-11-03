import re, difflib, sys
def sents(s):
    s = re.sub(r'```.*?```', '[CODE]', s, flags=re.S)
    out = []
    for line in s.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith('#'): out.append(line); continue
        out += [x + '。' for x in re.split(r'。', line) if x.strip()]
    return out
for t in sys.argv[1:]:
    T3, F, W = [sents(open(f'{t}_{k}.md').read()) for k in ('T3', 'F', 'W')]
    for name, a, b in (('T3→F', T3, F), ('F→W', F, W)):
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        same = sum(i2 - i1 for op, i1, i2, j1, j2 in sm.get_opcodes() if op == 'equal')
        print(f'\n===== {t} {name}  文数 {len(a)}→{len(b)}  そのまま残った文 {same}')
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'equal': continue
            for x in a[i1:i2]: print('  - ' + x)
            for x in b[j1:j2]: print('  + ' + x)
