import sys, os, re, collections
from lxml import etree

ROOT = sys.argv[1]
EPUBTYPE = '{http://www.idpf.org/2007/ops}type'
BODY = ['preface001', 'preface002', 'preface003', 'preface004', 'preface005', 'preface006',
        'preface007', 'preface008', 'preface010', 'chapter001', 'chapter001-01', 'chapter001-02',
        'chapter001-03', 'chapter002', 'chapter002-01', 'chapter002-02', 'chapter003',
        'chapter003-01', 'chapter003-02', 'chapter003-03', 'chapter003-04']
FN = ['footnotes', 'footnotesa', 'footnotesb', 'footnotesc']
EN = ['notes001', 'notes002', 'notes003']
docs = {n: etree.parse(os.path.join(ROOT, n + '.xhtml')) for n in BODY + FN + EN}
SER = lambda el: etree.tostring(el, encoding='unicode', with_tail=False)

def raw(n):
    return open(os.path.join(ROOT, n + '.xhtml'), encoding='utf-8').read()

def strip(s):
    s = re.sub(r'<a class="noteref"[^>]*>[^<]*</a>', '', s)
    s = re.sub(r'<span epub:type="pagebreak"[^>]*/>', '', s)
    return re.sub(r'<[^>]+>', '', s)

def ctx(n, pat, k=3, w=140, flags=0):
    s = raw(n)
    out = []
    for m in re.finditer(pat, s, flags):
        a, b = max(0, m.start() - w), min(len(s), m.end() + w)
        out.append(s[a:b].replace('\n', ' '))
        if len(out) >= k:
            break
    return out

def section(title):
    print('\n##### ' + title)

section('curly-brace glyphs ⎧⎨⎩ by file')
for n in BODY + FN:
    c = raw(n).count('⎨')
    if c:
        print(n, c, ctx(n, '⎨', 1, 300)[0][:600])

section('ß contexts')
for n in BODY + FN:
    for c in ctx(n, 'ß', 3, 60):
        print(n, '|', c)

section('Greek in markup context (first 2 per file)')
for n in BODY + FN:
    for c in ctx(n, r'[Ͱ-Ͽἀ-῿]+', 2, 90):
        print(n, '|', c)

section('ανία / combining U+0313 / U+02BC contexts')
for n in BODY + FN:
    for p in ('ανία', '̓', 'ʼ', ' '):
        for c in ctx(n, re.escape(p), 2, 80):
            print(n, repr(p), '|', c)

section('mentions of Hebrew/Arabic/Syriac/Chaldee')
for n in BODY + FN:
    for c in ctx(n, r'Hebrew|Hebrews? word|Arabic|Syriac|Chaldee', 3, 100):
        print(n, '|', strip(c))

section('endnote double ref chh3_en_30 / chi3_en_30')
for n in BODY:
    for c in ctx(n, r'ch[hi]3_en_30"', 3, 200):
        print(n, '|', c)
for c in ctx('notes003', r'id="ch[hi]3_en_30"', 2, 400):
    print('notes003 |', c)

section('pagebreak gaps inside running text (not at file boundaries)')
prev = None
for n in BODY:
    for el in docs[n].iter():
        if el.get(EPUBTYPE) == 'pagebreak':
            m = re.match(r'pg(\d+)$', el.get('id') or '')
            if not m:
                print('non-numeric pagebreak', n, el.get('id'))
                continue
            v = int(m.group(1))
            if prev and prev[0] == n and v != prev[1] + 1:
                print(f'  {n}: {prev[1]} -> {v}')
            prev = (n, v)

section('pagebreak splitting a word (letter on both sides)')
cnt = 0; ex = []
for n in BODY:
    for m in re.finditer(r'([A-Za-z])<span epub:type="pagebreak" id="(pg\d+)"/>([a-z])', raw(n)):
        cnt += 1; ex.append((n, m.group(0)))
print(cnt, ex[:8])

section('noterefs inside headings / inside footnotes / inside blockquote verse')
for n in BODY:
    for h in docs[n].iter('{*}h2', '{*}h3', '{*}h4'):
        for a in h.iter('{*}a'):
            print('heading noteref', n, h.get('id'), strip(SER(h))[:120])
fnn = sum(1 for n in FN for a in docs[n].iter('{*}a') if a.get(EPUBTYPE) == 'noteref')
print('noterefs inside footnote files:', fnn)

section('lucida / arial_bold / sup / sup_it / small_caps samples')
for cls in ('lucida', 'arial_bold', 'sup_it', 'sup'):
    seen = collections.Counter()
    for n in BODY + FN:
        for el in docs[n].iter('{*}span'):
            if el.get('class') == cls:
                seen[''.join(el.itertext())] += 1
    print(cls, seen.most_common(15))
sc = collections.Counter()
for n in BODY + FN:
    for el in docs[n].iter('{*}span'):
        if el.get('class') == 'small_caps':
            t = ''.join(el.itertext())
            sc['UPPER' if t.isupper() else ('lower' if t.islower() else 'mixed')] += 1
print('small_caps text case:', sc)

section('figures in body')
for n in BODY:
    for f in docs[n].iter('{*}figure'):
        img = f.find('.//{*}img')
        print(n, f.get('class'), img.get('src') if img is not None else None, repr(img.get('alt')) if img is not None else '')

section('bracket analysis (body files)')
tot = collections.Counter()
for n in BODY:
    s = raw(n)
    tot['[ total'] += s.count('[')
    tot['after </em> ['] += len(re.findall(r'</em>\s*\[', s))
    tot['inside <p class=... TS'] += len(re.findall(r'<p class="[^"]*\bTS\d?\b', s))
    tot['[Translation] header'] += s.count('[Translation]')
    tot['[ in non-em context'] += len(re.findall(r'(?<!</em>)(?<!</em> )\[', s))
print(tot)
print('examples of [ not right after </em>:')
k = 0
for n in BODY:
    for m in re.finditer(r'(?<!</em>)(?<!</em> )\[[^\]]{0,120}\]', raw(n)):
        s = raw(n); print(' ', n, '|', strip(s[max(0, m.start()-120):m.end()+20]).replace('\n', ' '))
        k += 1
        if k > 14: break
    if k > 14: break

section('braces (editorial interpolations) examples')
k = 0
for n in BODY + FN:
    for m in re.finditer(r'\{[^}]{0,100}\}', raw(n)):
        print(' ', n, '|', strip(m.group(0)))
        k += 1
        if k > 12: break
    if k > 12: break

section('italic fragmentation: adjacent <em>…</em>. <em> runs')
frag = sum(len(re.findall(r'</em>[.,;:]? ?<em>', raw(n))) for n in BODY + FN)
ems = sum(raw(n).count('<em>') for n in BODY + FN)
print('em elements:', ems, ' adjacent em-joins:', frag)

section('internal cross-reference patterns in body text')
xr = collections.Counter(); exs = []
pat = re.compile(r'(Part(?:it)?\.?\s*\d|Sect\.\s*\d|Memb\.\s*\d|Subsect\.\s*\d|as I have (?:shown|said|showed)|before (?:mentioned|cited)|in the precedent|in his place|following discourse)', re.I)
for n in BODY[9:]:
    t = strip(raw(n))
    for m in pat.finditer(t):
        xr[m.group(1)[:12].lower()] += 1
        if len(exs) < 12 and m.group(1).lower().startswith(('part', 'sect')):
            exs.append((n, t[max(0, m.start()-80):m.end()+60].replace('\n', ' ')))
print(xr.most_common(20))
for e in exs: print(' ', e)

section('footnote citation token frequencies (first 2 words after number)')
toks = collections.Counter()
for n in FN:
    for m in re.finditer(r'(?:lib|cap|tom|epist|consil|sect|part|memb|subs|tract|com|fol|pag|ser|hom|serm|lect|prob|aph|dist|quaest|art|dial|ode|sat|eleg|ep|c|l|ib|idem|ibid|op\. cit)\.', strip(raw(n)), re.I):
        toks[m.group(0).lower()] += 1
print(toks.most_common(40))

section('footnotes: length distribution and samples of long ones')
lens = []
for n in FN:
    for a in docs[n].iter('{*}aside'):
        lens.append((len(''.join(a.itertext())), n, a.get('id')))
lens.sort()
print('n=', len(lens), 'median', lens[len(lens)//2][0], 'max', lens[-3:])
for L, n, i in lens[-2:]:
    print(n, i, strip(SER(docs[n].xpath(f'//*[@id="{i}"]')[0]))[:700])

section('suspicious whitespace / punctuation')
for n in BODY + FN:
    s = strip(raw(n))
    a = len(re.findall(r' [,;:.](?!\.)', s)); b = len(re.findall(r'  +', s)); c = len(re.findall(r'[a-z]-\s+[a-z]', s))
    d = len(re.findall(r'\w\(\w', s));
    if a or c: print(f'  {n}: space-before-punct={a} double-space={b} hyphen-space={c}')
