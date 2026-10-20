"""Language identification, M1 rules (SPEC §6.1, steps 1-4).

Deterministic script tagging for Greek, Hebrew and Arabic; rule-based Latin detection over
italic runs using English/Latin function words, Latin endings and Gowland's brackets as context.
No language-detector library is used. Every decision records its confidence and method.
"""

import regex as re

from ..tei import ED, XML_LANG, T, el, local, put_items, take_items

GREEK_CH = r"\p{Script=Greek}"
# A run starts at a Greek letter (or a breathing typed as a modifier letter before one) and continues
# over Greek letters, combining marks, elision marks, and spaces/punctuation that lead to more Greek.
GREEK_RUN = re.compile(
    r"[ʼˋ]*\p{Script=Greek}"
    r"(?:[\p{Script=Greek}\p{M}ʼʽˋ’']"
    r"|[\s,.;:·](?=[\s,.;:·]*[ʼˋ]*\p{Script=Greek}))*"
)
SCRIPTS = [("grc", GREEK_RUN), ("he", re.compile(r"\p{Script=Hebrew}+(?:\s+\p{Script=Hebrew}+)*")),
           ("ar", re.compile(r"\p{Script=Arabic}+(?:\s+\p{Script=Arabic}+)*"))]
LATIN_NEXT_TO_GREEK = re.compile(rf"\p{{Script=Latin}}{GREEK_CH}|{GREEK_CH}\p{{Script=Latin}}")

EN_FUNCTION = set("""
the of and to that is was be been it his her him he she they them their this these those with
for by or not which who whom what when where there here from as are were have hath has had
doth do did does shall should will would may might can could must upon unto into than then
so such our your my mine thy thee thou ye we us all any every no nor yet but if though how
why also more most very many much some other others own same being an
""".split())
LA_FUNCTION = set("""
et est sunt non ut cum quod qui quae quam quid quis sed nec neque enim autem vel aut sic tam
ad de ex e ab per pro sine sub super inter apud ob propter ac atque ne nisi si etiam ita
hic haec hoc ille illa illud ipse ipsa iste nihil omnia omnes omnis esse fuit erat erit sit
sint sum es nam tamen quoque ubi unde semper nunc tunc iam jam modo vero ergo igitur quasi
quoniam quia dum donec mihi tibi sibi nos vos me te se eius ejus suus sua suum meus mea
tuus tua noster nostra vester qui quo qua quibus cui cuius cujus deus dei deo
""".split())
LA_ENDINGS = re.compile(r"(?:orum|arum|ibus|ntur|tur|bant|bunt|erunt|isse|iis|ae|um|que|ii|ium)$")
CITATION = re.compile(r"\d|\b(?:lib|cap|sect|tom|epist|consil|fol|memb|subs|c|l)\.", re.I)
PUNCT_ONLY = re.compile(r"^[\s,.;:!?&()\-—’']*$")
WORD = re.compile(r"[\p{L}\p{M}’']+")


# ------------------------------------------------------------------ scripts

def _wrap_script_runs(e, stats) -> None:
    if e.tag in (ED("enref"), T("pb"), T("lb")):
        return
    if e.get(XML_LANG) is not None and e.get(XML_LANG) != "en":
        return  # already language-marked as a whole
    items = take_items(e)
    out = []
    for it in items:
        if not isinstance(it, str):
            out.append(it)
            continue
        pos = 0
        spans = []
        for lang, rx in SCRIPTS:
            spans += [(m.start(), m.end(), lang) for m in rx.finditer(it)]
        for s, t, lang in sorted(spans):
            if s < pos:
                continue
            out.append(it[pos:s])
            f = el("foreign", {"lang-tmp": lang, "resp": "#rules", "cert": "high", "ana": "foreign",
                               "type": "script"})
            f.text = it[s:t]
            out.append(f)
            stats[f"script:{lang}"] += 1
            pos = t
        out.append(it[pos:])
    put_items(e, out)
    for c in list(e):
        if isinstance(c.tag, str) and c.get("lang-tmp") is None:
            _wrap_script_runs(c, stats)


def _letters(s: str, script: str) -> int:
    return len(re.findall(rf"\p{{Script={script}}}", s))


def tag_verse_groups(div, stats) -> None:
    """A verse group that is wholly Greek is marked at lg level (one passage, not one per line)."""
    for lg in div.iter(T("lg")):
        if lg.getparent().tag == ED("verse-trans") or lg.get("type") == "translation-block":
            continue
        text = "".join(lg.itertext())
        g, lat = _letters(text, "Greek"), _letters(text, "Latin")
        if g and g >= 0.9 * (g + lat):
            lg.set(XML_LANG, "grc")
            lg.set("ana", "foreign")
            lg.set("resp", "#rules")
            lg.set("cert", "high")
            stats["lg:grc"] += 1


def flag_mixed_script(div) -> list[str]:
    return [m.group(0) for m in LATIN_NEXT_TO_GREEK.finditer("".join(div.itertext()))]


# ------------------------------------------------------------------ Latin (italic runs)

def _is_italic(x) -> bool:
    return not isinstance(x, str) and x.tag == T("hi") and x.get("rend") == "i"


NAME_PARTICLES = {"de", "a", "ab", "van", "von", "of", "the", "à", "la", "le", "du", "di", "da", "&"}


def classify(text: str, followed_by_bracket: bool, in_note: bool = False) -> tuple[str, str, str]:
    """-> (verdict, confidence, reason). verdict: la | en | name | citation | undetermined.

    `undetermined` means the rules cannot decide; it is left untagged and goes to the review queue
    (model adjudication arrives in M2). It is never silently counted as English.
    """
    words = WORD.findall(text)
    lower = [w.lower().strip("’'") for w in words]
    if not words:
        return "en", "high", "no words"
    if CITATION.search(text) and not followed_by_bracket:
        return "citation", "medium", "locator abbreviation or digits"
    n_en = sum(w in EN_FUNCTION for w in lower)
    n_la = sum(w in LA_FUNCTION or bool(LA_ENDINGS.search(w)) for w in lower)
    if followed_by_bracket and n_en == 0:
        return "la", "high", f"Gowland bracket follows; la={n_la} en=0"
    content = [w for w in words if w.lower() not in NAME_PARTICLES]
    if content and len(content) <= 4 and all(w[:1].isupper() for w in content) and n_en == 0:
        return "name", "medium", "capitalised words only (name or term)"
    if in_note and len(words) <= 6 and n_la < 2:
        # Gowland translated the Latin that survives in sidenotes, so unbracketed short runs
        # there are almost always titles or citations.
        return "citation", "medium", f"short unbracketed run in a sidenote (la={n_la} en={n_en})"
    if n_la and n_la > n_en and n_en <= 1:
        return "la", ("high" if n_la >= 2 else "medium"), f"la={n_la} en={n_en}"
    if n_en:
        return "en", ("high" if n_en >= 2 else "medium"), f"la={n_la} en={n_en}"
    return "undetermined", "low", f"no function words (la={n_la} en=0)"


def _runs(items: list) -> list[tuple[int, int]]:
    """Index ranges [i, j) of maximal italic runs joined only by punctuation/space strings.

    A run that is really a comma-separated list of short italic items ("Galen, Aretaeus, Rhasis")
    is split back into one run per item, so each item is classified on its own.
    """
    runs, i = [], 0
    while i < len(items):
        if _is_italic(items[i]):
            j = i + 1
            while j + 1 < len(items) and isinstance(items[j], str) and PUNCT_ONLY.match(items[j]) \
                    and _is_italic(items[j + 1]):
                j += 2
            members = list(range(i, j, 2))
            seps = [items[k] for k in range(i + 1, j, 2)]
            short = all(len(WORD.findall(text_of([items[m]]))) <= 3 for m in members)
            if len(members) > 1 and short and seps and all(s.strip() == "," for s in seps):
                runs.extend((m, m + 1) for m in members)
            else:
                runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def text_of(nodes: list) -> str:
    """Text of items, leaving out sidenotes (their text belongs to the note, not the run)."""
    out = []

    def walk(x):
        if x.tag == T("note"):
            return
        if x.text:
            out.append(x.text)
        for c in x:
            walk(c)
            if c.tail:
                out.append(c.tail)

    for n in nodes:
        if isinstance(n, str):
            out.append(n)
        else:
            walk(n)
    return "".join(out)


def _next_is_bracket(items: list, j: int) -> bool:
    k = j
    while k < len(items) and isinstance(items[k], str) and not items[k].strip():
        k += 1
    return k < len(items) and not isinstance(items[k], str) and items[k].tag == ED("trans")


def tag_latin(e, decisions: list, unit: str, in_note: bool = False) -> None:
    if e.tag in (ED("trans"), ED("verse-trans"), T("foreign")) or e.get("ana") == "foreign":
        return
    if e.get("resp") == "#editor":  # our own transcriptions are not source text
        return
    in_note = in_note or e.tag == T("note")
    items = take_items(e)
    out, last = [], 0
    for i, j in _runs(items):
        text = text_of(items[i:j])
        verdict, conf, why = classify(text, _next_is_bracket(items, j), in_note)
        decisions.append({"unit": unit, "text": text, "verdict": verdict, "confidence": conf, "why": why,
                          "in_note": in_note})
        out.extend(items[last:i])
        if verdict == "la":
            f = el("foreign", {"lang-tmp": "la", "resp": "#rules", "cert": conf, "ana": "foreign"})
            put_items(f, items[i:j])
            out.append(f)
        else:
            out.extend(items[i:j])
        last = j
    out.extend(items[last:])
    put_items(e, out)
    for c in list(e):
        if isinstance(c.tag, str):
            tag_latin(c, decisions, unit, in_note)


def tag_verse_latin(div, decisions: list, unit: str) -> None:
    """Verse groups followed by a translation group and made of Latin italics: lg-level Latin."""
    for q in div.iter(T("quote")):
        kids = [k for k in q if isinstance(k.tag, str)]
        for a, b in zip(kids, kids[1:], strict=False):
            if a.tag != T("lg") or a.get("ana") == "foreign":
                continue
            followed = b.tag == ED("verse-trans") or b.get("type") == "translation-block"
            text = text_of([a])
            ital = "".join(text_of([h]) for h in a.iter(T("hi"))
                           if h.get("rend") == "i" and not any(x.tag == T("note") for x in h.iterancestors()))
            verdict, conf, why = classify(ital or text, followed)
            if followed and verdict == "la":
                a.set(XML_LANG, "la")
                a.set("ana", "foreign")
                a.set("resp", "#rules")
                a.set("cert", conf)
                decisions.append({"unit": unit, "text": text.strip(), "verdict": "la", "confidence": conf,
                                  "why": "verse group followed by translation; " + why})


def finalize_lang(div) -> None:
    for f in div.iter(T("foreign")):
        f.set(XML_LANG, f.attrib.pop("lang-tmp"))


def run(div, unit: str, stats) -> list[dict]:
    decisions: list[dict] = []
    tag_verse_groups(div, stats)
    _wrap_script_runs(div, stats)
    tag_verse_latin(div, decisions, unit)
    tag_latin(div, decisions, unit)
    finalize_lang(div)
    for d in decisions:
        stats[f"italic-run:{d['verdict']}"] += 1
    return decisions


def is_foreign(x) -> bool:
    return not isinstance(x, str) and (local(x.tag) == "foreign" or x.get("ana") == "foreign")
