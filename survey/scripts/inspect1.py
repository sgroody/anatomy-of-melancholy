import sys, os, re, collections, json
from lxml import etree

ROOT = sys.argv[1]  # .../EPUB/xhtml
NS = {'h': 'http://www.w3.org/1999/xhtml', 'epub': 'http://www.idpf.org/2007/ops'}
EPUBTYPE = '{http://www.idpf.org/2007/ops}type'
BODY = ['preface001', 'preface002', 'preface003', 'preface004', 'preface005', 'preface006',
        'preface007', 'preface008', 'preface010', 'chapter001', 'chapter001-01', 'chapter001-02',
        'chapter001-03', 'chapter002', 'chapter002-01', 'chapter002-02', 'chapter003',
        'chapter003-01', 'chapter003-02', 'chapter003-03', 'chapter003-04']
FN = ['footnotes', 'footnotesa', 'footnotesb', 'footnotesc']
EN = ['notes001', 'notes002', 'notes003']

def load(name):
    return etree.parse(os.path.join(ROOT, name + '.xhtml'))

docs = {n: load(n) for n in BODY + FN + EN}
ids = {}
dupe_ids = []
for n, d in docs.items():
    for el in d.iter():
        i = el.get('id')
        if i:
            if (n, i) in ids:
                dupe_ids.append((n, i))
            ids[(n, i)] = el

def text(el):
    return ''.join(el.itertext())

# --- noterefs
refs = collections.Counter()
broken = []
ref_targets = collections.Counter()
fn_marker_seq = collections.defaultdict(list)
for n in BODY:
    for a in docs[n].iter('{*}a'):
        if a.get(EPUBTYPE) == 'noteref':
            href = a.get('href')
            f, _, frag = href.partition('#')
            f = f.replace('.xhtml', '')
            kind = 'fn' if f in FN else ('en' if f in EN else 'other:' + f)
            refs[(n, kind)] += 1
            ref_targets[(f, frag)] += 1
            if (f, frag) not in ids:
                broken.append((n, a.get('id'), href))
            if kind == 'fn':
                fn_marker_seq[n].append(text(a))
print('NOTEREFS by file/kind:')
for k in sorted(refs):
    print('  ', k, refs[k])
print('broken noterefs:', len(broken), broken[:10])
multi = [(k, v) for k, v in ref_targets.items() if v > 1]
print('note targets referenced >1 times:', len(multi), multi[:10])

# --- footnote/endnote asides
def asides(names, cls=None):
    out = []
    for n in names:
        for el in docs[n].iter('{*}aside'):
            out.append((n, el))
    return out

for label, names in (('footnotes', FN), ('endnotes', EN)):
    al = asides(names)
    unref = [(n, el.get('id')) for n, el in al if ref_targets[(n, el.get('id'))] == 0]
    badback = []
    for n, el in al:
        bl = el.find('.//{*}a[@class="backlink"]')
        if bl is None:
            badback.append((n, el.get('id'), 'no backlink'))
            continue
        f, _, frag = bl.get('href').partition('#')
        if (f.replace('.xhtml', ''), frag) not in ids:
            badback.append((n, el.get('id'), bl.get('href')))
    print(f'{label}: asides={len(al)} unreferenced={len(unref)} {unref[:8]} bad backlinks={len(badback)} {badback[:8]}')

print('duplicate ids:', len(dupe_ids), dupe_ids[:10])

# footnote marker numbering: does it restart / skip?
for n, seq in fn_marker_seq.items():
    nums = [int(re.sub(r'\D', '', s) or -1) for s in seq]
    jumps = [(i, nums[i-1], nums[i]) for i in range(1, len(nums)) if nums[i] != nums[i-1] + 1]
    print(f'  fn markers {n}: n={len(nums)} first={nums[:1]} last={nums[-1:]} non-sequential={len(jumps)} {jumps[:6]}')

# --- scripts
GREEK = re.compile(r'[Ͱ-Ͽἀ-῿]+')
HEB = re.compile(r'[֐-׿יִ-ﭏ]+')
ARAB = re.compile(r'[؀-ۿ]+')
for label, rx in (('Greek', GREEK), ('Hebrew', HEB), ('Arabic', ARAB)):
    for n in BODY + FN:
        t = text(docs[n].getroot())
        runs = rx.findall(t)
        if runs:
            print(f'{label} runs in {n}: {len(runs)} chars={sum(map(len, runs))} e.g. {runs[:5]}')

# non-ASCII char inventory in body + fn
cc = collections.Counter()
for n in BODY + FN:
    for ch in text(docs[n].getroot()):
        if ord(ch) > 127:
            cc[ch] += 1
print('non-ASCII chars:', ' '.join(f'{c}(U+{ord(c):04X}):{k}' for c, k in cc.most_common(120)))

# --- brackets & braces in body / fn
for n in BODY + FN:
    t = text(docs[n].getroot())
    sq = len(re.findall(r'\[', t)); sqc = len(re.findall(r'\]', t))
    br = len(re.findall(r'\{', t)); brc = len(re.findall(r'\}', t))
    print(f'  {n}: [={sq} ]={sqc} {{={br} }}={brc}')

# --- page breaks
pbs = []
for n in BODY:
    for el in docs[n].iter():
        if el.get(EPUBTYPE) == 'pagebreak':
            pbs.append((n, el.get('id')))
nums = [(n, i) for n, i in pbs]
print('pagebreaks in body:', len(pbs), 'first', pbs[:2], 'last', pbs[-2:])
prev = None
gaps = []
for n, i in pbs:
    m = re.match(r'pg(\d+)$', i or '')
    if not m:
        continue
    v = int(m.group(1))
    if prev is not None and v != prev + 1:
        gaps.append((n, prev, v))
    prev = v
print('pagebreak gaps:', len(gaps), gaps[:20])
