import sys, os, re, collections
from lxml import etree

ROOT = sys.argv[1]
EPUBTYPE = '{http://www.idpf.org/2007/ops}type'
CH = ['chapter001-01', 'chapter001-02', 'chapter001-03', 'chapter002-01', 'chapter002-02',
      'chapter003-01', 'chapter003-02', 'chapter003-03', 'chapter003-04']
FN = ['footnotes', 'footnotesa', 'footnotesb', 'footnotesc']
docs = {n: etree.parse(os.path.join(ROOT, n + '.xhtml')) for n in CH + FN + ['preface006', 'nav']}
ser = lambda el: etree.tostring(el, encoding='unicode', with_tail=False)

def txt(el):
    # text without noterefs
    parts = []
    def walk(e):
        if e.get(EPUBTYPE) == 'noteref':
            return
        if e.text: parts.append(e.text)
        for c in e:
            walk(c)
            if c.tail: parts.append(c.tail)
    walk(el)
    return re.sub(r'\s+', ' ', ''.join(parts)).strip()

print('### heading-image figures in chapters')
for n in CH:
    for f in docs[n].iter('{*}figure'):
        print(n, ser(f)[:400].replace('\n', ' '))
        prev = f.getprevious(); nxt = f.getnext()
        print('   prev:', ser(prev)[:200].replace('\n', ' ') if prev is not None else None)
        print('   next:', ser(nxt)[:200].replace('\n', ' ') if nxt is not None else None)

print('\n### structural heading walk')
part = 0
state = {'sect': None, 'memb': None, 'subs': None}
units = []
anoms = []
for n in CH:
    if n.endswith('-01'):
        part += 1
        state = {'sect': None, 'memb': None, 'subs': None}
    for h in docs[n].iter('{*}h2', '{*}h3', '{*}h4'):
        t = txt(h)
        cls = h.get('class')
        nums = re.findall(r'(SUBSECT|SECT|MEMB)\.?\s*(\d+)', t.upper())
        if nums:
            for k, v in nums:
                v = int(v)
                key = {'SECT': 'sect', 'MEMB': 'memb', 'SUBSECT': 'subs'}[k]
                old = state[key]
                if key == 'sect':
                    if old is not None and v != old + 1: anoms.append((n, h.get('id'), f'Sect {old}->{v}'))
                    state.update(sect=v, memb=None, subs=None)
                elif key == 'memb':
                    if old is not None and v != old + 1: anoms.append((n, h.get('id'), f'Memb {old}->{v}'))
                    state.update(memb=v, subs=None)
                else:
                    if old is not None and v != old + 1: anoms.append((n, h.get('id'), f'Subsect {old}->{v}'))
                    state.update(subs=v)
            print(f'  {n} {h.tag[-2:]}.{cls:18} {t[:60]!r:62} -> P{part} S{state["sect"]} M{state["memb"]} s{state["subs"]}')
        elif cls in ('HeadA0', 'HeadA'):
            units.append((part, state['sect'], state['memb'], state['subs'], t[:70], n, h.get('id')))
        else:
            print(f'  {n} {h.tag[-2:]}.{cls:18} {t[:80]!r}')
print('numbering anomalies:', anoms)
print('titled units:', len(units))
nav = [re.sub(r'\s+', ' ', ''.join(a.itertext())) for a in docs['nav'].iter('{*}a')]
navu = [x for x in nav if re.match(r'\d\.\d+\.\d+\.\d+ ', x)]
print('nav subsection entries:', len(navu))
navkeys = [tuple(map(int, x.split(' ')[0].split('.'))) for x in navu]
unitkeys = [(p, s, m, u) for p, s, m, u, *_ in units]
print('nav keys not in heading walk:', [k for k in navkeys if k not in unitkeys][:20])
print('heading-walk keys not in nav:', [k for k in unitkeys if k not in navkeys][:20])
dup = [k for k, c in collections.Counter(unitkeys).items() if c > 1]
print('duplicate unit keys:', dup)
for p in (1, 2, 3):
    print(f'  Partition {p}: sections={len({k[1] for k in unitkeys if k[0]==p})} members={len({k[:3] for k in unitkeys if k[0]==p})} subsection-units={sum(1 for k in unitkeys if k[0]==p)}')

print('\n### Burton footnotes: share containing brackets / Latin-only etc.')
c = collections.Counter()
samples = collections.defaultdict(list)
for n in FN:
    for a in docs[n].iter('{*}aside'):
        t = txt(a)
        t = re.sub(r'^\d+\.\s*', '', t)
        has_br = '[' in t
        c['total'] += 1
        if has_br: c['with [translation]'] += 1
        if re.search(r'\b(lib|cap|c|l|epist|tom|consil)\.', t, re.I): c['with lib./cap./etc.'] += 1
        if len(t) < 25: c['short (<25 chars)'] += 1
        if re.fullmatch(r"[A-Z][a-z]+\.?", t): c['bare single name'] += 1; samples['bare'].append(t)
        if re.search(r'\bIdem\b|\bIbid', t): c['idem/ibid'] += 1
        if re.search(r'\bvide\b|\bsee\b', t, re.I): c['vide/see'] += 1
print(c)
print('bare-name examples:', collections.Counter(samples['bare']).most_common(30))

print('\n### random footnote samples')
import random
random.seed(7)
allas = [(n, a) for n in FN for a in docs[n].iter('{*}aside')]
for n, a in random.sample(allas, 25):
    print(' ', n, a.get('id'), '|', txt(a)[:220])
