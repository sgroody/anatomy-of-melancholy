import sys, os, re
from lxml import etree
R = sys.argv[1]
CH = ['chapter001-01','chapter001-02','chapter001-03','chapter002-01','chapter002-02','chapter003-01','chapter003-02','chapter003-03','chapter003-04']
seen_num = False; missing = []; total = 0
for n in CH:
    d = etree.parse(os.path.join(R, n + '.xhtml'))
    for el in d.getroot().iter('{*}h2','{*}h3','{*}h4','{*}figure'):
        t = ''.join(el.itertext()).upper()
        if el.tag.endswith('figure') or re.search(r'SUBSECT|MEMB|SECT', t):
            seen_num = True
        elif el.get('class') in ('HeadA', 'HeadA0'):
            total += 1
            if not seen_num:
                missing.append((n, el.get('id'), ''.join(el.itertext())[:50]))
            seen_num = False
print('titled units', total, 'without preceding number heading', len(missing))
for m in missing: print('  ', m)
# synopsis hidden text
for n in ['chapter001','chapter002','chapter003']:
    d = etree.parse(os.path.join(R, n + '.xhtml'))
    ps = [''.join(p.itertext()).strip() for t in d.getroot().iter('{*}table') for p in t.iter('{*}p')]
    br = sum(1 for p in ps if p in '⎧⎨⎩')
    ids = [int(re.sub(r'\D','',p.get('id'))) for t in d.getroot().iter('{*}table') for p in t.iter('{*}p') if re.sub(r'\D','',p.get('id') or '')]
    inv = sum(1 for a,b in zip(ids, ids[1:]) if b < a)
    print(n, 'synopsis <p>:', len(ps), 'brace-glyph-only <p>:', br, 'id order inversions:', inv)
