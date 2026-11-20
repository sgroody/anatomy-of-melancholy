"""Language identification, M1 rules (SPEC §6.1, steps 1-4).

Deterministic script tagging for Greek, Hebrew and Arabic; rule-based Latin detection over
italic runs using English/Latin function words, Latin endings and Gowland's brackets as context.
No language-detector library is used. Every decision records its confidence and method.
"""

import functools

import regex as re
import yaml

from .. import paths
from ..tei import ED, XML_LANG, T, el, local, put_items, take_items
from . import lexicon

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
suos suas suis suae suo suam sui meos meas meis meum meam meo mei tuos tuas tuis tuum tuam tuo tui
nostri nostro nostros nostras nostris nostrum vestri vestros vestris eos eas eis eum eam illi illis illos
illas illum illam illo hunc hanc hujus huius horum harum
""".split())  # 2026-11-18: pronoun and possessive forms (after held-out h3: "Deos suos patrio more venerantur")
LA_ENDINGS = re.compile(r"(?:orum|arum|ibus|ntur|tur|bant|bunt|erunt|isse|iis|ae|um|que|ii|ium)$")
# "&c." is "etc.", not the locator "c." (chapter), hence the look-behind
CITATION = re.compile(r"\d|(?<!&)\b(?:lib|cap|sect|tom|epist|consil|fol|memb|subs|c|l)\.|^\s*(?:idem|ibid|ib)\b"
                      r"|^\s*[ivxlcdm]{1,6}\.?\s*$", re.I)
# A work cited by author and title: "Grotius de verit.", "Levinus Lemnius de occult." — one to three
# capitalised words, "de", and a title word cut off by an abbreviation stop.
WORK_TITLE = re.compile(r"^\s*(?:\p{Lu}[\p{L}’']*\.?\s+){1,3}de\s+\p{L}+\.")
TITLE_WORDS = {"de", "in", "&", "et"}
# "Originem in Celsum", "vide Cyrillum in Julianum": an author and the work against or on another (2026-11-19, h4)
AUTHOR_IN = re.compile(r"^\s*(?:(?:vide|vid|cf)\.?\s+)?(?:\p{Lu}[\p{L}’']*\.?\s+){1,2}(?:in|contra|adversus)\s+"
                       r"\p{Lu}[\p{L}’']*\.?\s*$")
REF_WORDS = TITLE_WORDS | {"contra", "adversus", "vide", "vid", "cf"}
# a locator and nothing else: "20 & passim alias", "38 & deinceps" (Gowland may translate it; it is still a
# reference, not Burton's Latin: 2026-11-19, after held-out h4)
LOCATOR_WORDS = {"passim", "alias", "alibi", "deinceps", "seq", "sequ", "sequent", "sequentibus", "sqq", "ibid",
                 "ibidem", "infra", "supra", "et", "c", "cap", "lib", "fol", "pag", "tom", "num", "sect"}


def _locator_only(text: str) -> bool:
    words = [w.lower() for w in WORD.findall(text)]
    return bool(words) and bool(re.search(r"\d", text)) and all(w in LOCATOR_WORDS for w in words)


@functools.cache
def naturalised() -> frozenset[str]:
    """Latin words naturalised in English before 1621 (data/manual/naturalised.yaml)."""
    path = paths.MANUAL / "naturalised.yaml"
    if not path.exists():
        return frozenset()
    return frozenset(w.lower() for w in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("words", {}))
ABBREV = {"lib", "cap", "sect", "tom", "epist", "ep", "consil", "fol", "memb", "subs", "subsect", "c", "l", "de",
          "com", "hist", "lect", "ser", "serm", "hom", "sat", "dial", "art", "quaest", "tract", "prob", "aph",
          "par", "vers", "pag", "num", "cent", "obs", "observ", "exercit", "med", "pract", "instit", "comment"}
# Italic fragments are joined into one run across spaces, commas, full stops and &, but never across
# : ; ? ! — Burton often italicises an English clause and then a Latin one ("…their souls: Pars fati fuit").
PUNCT_ONLY = re.compile(r"^[\s,.&()\-—’']*$")
WORD = re.compile(r"[\p{L}\p{M}’']+")


# ------------------------------------------------------------------ scripts

def _wrap_script_runs(e, stats, gowland: bool = False) -> None:
    """Tag Greek/Hebrew/Arabic runs. Inside Gowland's matter they get a language but are not
    translation passages (no ana="foreign"): they must never be queued for a model."""
    if e.tag in (ED("enref"), T("pb"), T("lb")):
        return
    gowland = (gowland or e.tag in (ED("trans"), ED("verse-trans"), ED("block"))
               or (e.tag == T("supplied") and e.get("resp") == "#gowland") or e.get("resp") == "#gowland")
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
            f = el("foreign", {"lang-tmp": lang, "resp": "#rules", "cert": "high",
                               "ana": None if gowland else "foreign", "type": "script"})
            f.text = it[s:t]
            out.append(f)
            stats[f"script:{lang}"] += 1
            pos = t
        out.append(it[pos:])
    put_items(e, out)
    for c in list(e):
        if isinstance(c.tag, str) and c.get("lang-tmp") is None:
            _wrap_script_runs(c, stats, gowland)


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
    # "sup-i": a raised italic ending glued to an italic ordinal ("Si Venus in 12<sup>ma</sup>")
    return not isinstance(x, str) and x.tag == T("hi") and x.get("rend") in ("i", "sup-i")


def _alternate(items: list) -> list:
    """Put an empty string between directly adjacent elements, so run members sit at every other index (an
    empty separator means the two are glued: one word split by markup)."""
    out: list = []
    for it in items:
        if out and not isinstance(it, str) and not isinstance(out[-1], str):
            out.append("")
        out.append(it)
    return out


EN_LATIN_AMBIGUOUS = {"an", "his", "is", "do", "more", "me", "sub", "te", "nos", "per", "post", "sic", "ad"}
NAME_PARTICLES = {"de", "a", "ab", "van", "von", "of", "the", "à", "la", "le", "du", "di", "da", "&"}


def classify(text: str, followed_by_bracket: bool, in_note: bool = False,
             stop: bool = False) -> tuple[str, str, str]:
    """-> (verdict, confidence, reason). verdict: la | en | name | citation | undetermined.
    `stop`: a full stop follows the run (it may end in an abbreviation: "Austin de civ.").

    `undetermined` means the rules cannot decide; it is left untagged and goes to the review queue
    (model adjudication arrives in M2). It is never silently counted as English.
    """
    words = WORD.findall(ETC.sub(" ", text))  # "&c" is "etc.": no evidence either way
    lower = [w.lower().strip("’'") for w in words]
    if not words:
        return "en", "high", "no words"
    stopped = text.rstrip() + "." if stop else text
    if _locator_only(text):
        return "citation", "medium", "a locator only (digits and passim, deinceps …)"
    if len(words) == 1 and lower[0] in naturalised():
        return "en", "medium", "a Latin word naturalised in English (data/manual/naturalised.yaml)"
    if CITATION.search(stopped) and not followed_by_bracket:
        return "citation", "medium", "locator abbreviation or digits"
    if not followed_by_bracket and (ref := _reference_list(stopped)):
        return ref, "medium", ("authors and abbreviated titles (e.g. 'Grotius de verit.')" if ref == "citation"
                               else "a list of names")
    n_en = sum(w in EN_FUNCTION for w in lower)
    # "de" before a capitalised word is a name particle (Hercules de Saxonia), not Latin evidence
    n_la = sum((w in LA_FUNCTION or bool(LA_ENDINGS.search(w)))
               and not (w == "de" and k + 1 < len(words) and words[k + 1][:1].isupper())
               for k, w in enumerate(lower))
    # words that are also common Latin forms do not count as English evidence before a bracket
    n_en_strict = sum(w in EN_FUNCTION and w not in EN_LATIN_AMBIGUOUS for w in lower)
    if followed_by_bracket and n_en_strict == 0:
        return "la", "high", f"Gowland bracket follows; la={n_la} en={n_en}"
    # book lexicon evidence (never yields "high": the lexicon is built from high-confidence decisions)
    lex = [lexicon.latinness(w) for w in words if len(w) >= 3]
    lx_la, lx_en = lex.count("la"), lex.count("en")
    content = [w for w in words if w.lower() not in NAME_PARTICLES]
    if in_note and not followed_by_bracket and words[0] == "De" and len(words) <= 4:
        # "De Anima", "De Legibus" standing in a sidenote: a book's title (2026-11-18)
        return "citation", "medium", "a title (De …) in a sidenote"
    if content and len(content) <= 4 and all(w[:1].isupper() for w in content) and n_en == 0:
        long = [w for w in content if len(w) >= 3]
        if long and all(lexicon.latinness(w) == "la" for w in long):
            # every word must be attested lowercase in Burton's Latin, so personal names
            # (Donatus Altomarus) stay names while terms (Morbus Gallicus) become Latin
            return "la", "medium", f"capitalised term attested in Burton's Latin (lexicon la={lx_la})"
        return "name", "medium", "capitalised words only (name or term)"
    if in_note and not followed_by_bracket and len(words) <= 3 and words[0][:1].isupper():
        # a short unbracketed run opening with a capital in a sidenote is a title or an abbreviated name ("Vita
        # ejus", "Ter."): Gowland translated the Latin he kept in the notes, so a quotation there has his bracket
        # (2026-11-18, after held-out h2)
        return "citation", "medium", "short capitalised unbracketed run in a sidenote (a title)"
    if in_note and len(words) <= 6 and n_la < 2:
        if lx_la >= 2 and not lx_en and not n_en:
            return "la", "medium", f"sidenote run attested in Burton's Latin (lexicon la={lx_la})"
        # Gowland translated the Latin that survives in sidenotes, so unbracketed short runs
        # there are almost always titles or citations.
        return "citation", "medium", f"short unbracketed run in a sidenote (la={n_la} en={n_en})"
    if n_la and n_la > n_en and n_en <= 1:
        return "la", ("high" if n_la >= 2 else "medium"), f"la={n_la} en={n_en}"
    if n_la >= 2 and n_en_strict == 0 and lx_en <= lx_la:
        # the only "English" words are also Latin forms ("more", "his", "me"): 2026-11-18, after held-out h3
        return "la", "medium", f"la={n_la}; English words only Latin-ambiguous (en={n_en})"
    if n_en:
        return "en", ("high" if n_en >= 2 else "medium"), f"la={n_la} en={n_en}"
    if lx_la > lx_en:
        return "la", "medium", f"no function words; lexicon la={lx_la} en={lx_en}"
    if lx_en > lx_la:
        return "en", "medium", f"no function words; lexicon la={lx_la} en={lx_en}"
    return "undetermined", "low", f"no function words, lexicon silent (la={n_la} en=0)"


ETC = re.compile(r"&\s*c\b\.?")


def _capitalised(p: str) -> list[str] | None:
    """The words of a piece made of capitalised words only (particles and abbreviation stops allowed)."""
    words = [w for w in WORD.findall(p) if w.lower() not in NAME_PARTICLES]
    return words if words and all(w[:1].isupper() for w in words) else None


def _latin_term(words: list[str]) -> bool:
    """Every longer word is attested lowercase in Burton's Latin ('Morbus Gallicus' is a term, not a name)."""
    long = [w for w in words if len(w) >= 3]
    return bool(long) and all(lexicon.latinness(w) == "la" for w in long)


def _reference_list(text: str) -> str | None:
    """A list of references and names: every comma-separated piece (ignoring '&c') is an author-and-title
    reference ("Grotius de verit. Relig. Christianae") or a bare name ("Lessius, Morneus"), with no
    function word beyond the title particles. -> 'citation' if any piece is a reference, 'name' for a
    list of two or more names, else None."""
    pieces = [p for p in (ETC.sub(" ", x).strip() for x in re.split(r",\s*", text)) if WORD.search(p)]
    if not pieces:
        return None
    titles = [bool(WORK_TITLE.match(p) or AUTHOR_IN.match(p)) for p in pieces]
    caps = [_capitalised(p) for p, t in zip(pieces, titles, strict=True) if not t]
    # every piece a reference or capitalised, and most capitalised pieces names rather than Latin terms
    if not all(caps) or sum(_latin_term(c) for c in caps) * 2 > len(caps):
        return None
    lower = [w.lower() for w in WORD.findall(ETC.sub(" ", text))]
    allowed = REF_WORDS if any(titles) else TITLE_WORDS
    if any((w in LA_FUNCTION and w not in allowed) or w in EN_FUNCTION for w in lower):
        return None
    if any(titles):
        return "citation"
    return "name" if len(pieces) >= 2 else None


ROMAN_TOKEN = re.compile(r"[\p{L}\p{M}]+(?:['’][\p{L}]+)?|&|[^\s\p{L}\p{M}]+")
CLAUSE_STOP = set("():;?![]")


def tag_roman_before_brackets(div, decisions: list, unit: str) -> None:
    """Roman-type Latin directly before a Gowland bracket ("qui non Zelat, non amat [he who …]").

    Scans backwards from the bracket through the immediately preceding text only (never across
    elements), while words are Latin by the rules or the book lexicon; stops at the first English
    word or clause break. Needs >= 2 Latin words making >= 50 % of the span (a bracket follows and the
    span holds no English word). Confidence: medium.
    """
    for t in list(div.iter(ED("trans"))):
        prev = t.getprevious()
        if prev is not None and (prev.get("ana") == "foreign" or prev.tag == T("foreign")):
            continue
        # where the text before the bracket lives: the parent's text, the previous element's tail, or
        # (when the bracket directly follows an untagged italic run) the end of that italic run
        if prev is not None and prev.get("lang-title"):
            continue  # a book's title that Gowland translated (tag_latin decided it)
        inside = prev is not None and _is_italic(prev) and len(prev) == 0 and not (prev.tail or "").strip(" ,.;:")
        holder_is_tail = prev is not None and not inside
        text = (prev.text if inside else prev.tail if holder_is_tail else t.getparent().text) or ""
        toks = [m for m in ROMAN_TOKEN.finditer(text)]
        start = len(text.rstrip())
        la = other = 0
        for m in reversed(toks):
            w = m.group(0)
            if not re.match(r"[\p{L}&]", w):
                if any(ch in CLAUSE_STOP for ch in w) or (w.strip() in {".", "—"} and la):
                    break
                continue
            low = w.lower()
            is_la = w == "&" or low in LA_FUNCTION or bool(LA_ENDINGS.search(low)) or lexicon.latinness(w) == "la"
            is_en = (low in EN_FUNCTION and low not in LA_FUNCTION) or lexicon.latinness(w) == "en"
            if is_en and not is_la:
                break
            if is_la:
                la += 1
            else:
                other += 1
            start = m.start()
        span = text[start:].rstrip()
        span_len = len(text[start:len(text.rstrip())])
        if span and _locator_only(span):
            decisions.append({"unit": unit, "text": span.strip(), "verdict": "citation", "confidence": "medium",
                              "why": "roman locator before bracket (digits and passim, deinceps …)",
                              "in_note": any(a.tag == T("note") for a in t.iterancestors())})
            continue
        if la < 2 or la < 0.5 * (la + other) or not span:
            decisions.append({"unit": unit, "text": text[-60:].strip(), "verdict": "undetermined",
                              "confidence": "low", "why": f"roman text before bracket; la={la} other={other}",
                              "in_note": any(a.tag == T("note") for a in t.iterancestors())})
            continue
        f = el("foreign", {"lang-tmp": "la", "resp": "#rules", "cert": "medium", "ana": "foreign"})
        f.text = text[start:start + span_len]
        rest = text[start + span_len:]
        if inside:
            prev.text = text[:start]
            prev.insert(0, f)
        elif holder_is_tail:
            prev.tail = text[:start]
            prev.addnext(f)
        else:
            t.getparent().text = text[:start]
            t.getparent().insert(0, f)
        f.tail = rest
        decisions.append({"unit": unit, "text": f.text, "verdict": "la", "confidence": "medium",
                          "why": f"roman text before Gowland bracket; la={la} other={other}",
                          "in_note": any(a.tag == T("note") for a in t.iterancestors())})


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
            # a list of lowercase Latin words is one run ("horribile, dirum, pestilens, atrox, ferum"); only a list
            # with a capitalised member may be a list of names (2026-11-19, after held-out h4)
            caps = any(text_of([items[m]]).strip()[:1].isupper() for m in members)
            if len(members) > 1 and short and caps and seps and all(s.strip() == "," for s in seps):
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


def _next_is_bracket(items: list, j: int, through_stop: bool = False) -> bool:
    """A Gowland bracket follows directly, or (`through_stop`) after the run's own closing stop or comma."""
    k = j
    gap = r"\s*[.,]?\s*" if through_stop else r"\s*"
    while k < len(items) and isinstance(items[k], str) and re.fullmatch(gap, items[k]):
        k += 1
    return k < len(items) and not isinstance(items[k], str) and items[k].tag == ED("trans")


def _bracketed(items: list, i: int, j: int) -> bool:
    """A Gowland bracket translates the run. A bracket after the run's closing stop ("…&c. [Zanchius…")
    counts only for a run of >= 3 words that is not a string of abbreviations ("Lat. 10. Gr. Aust.
    [At latitude 10° south]" is a locator, not a passage)."""
    if _next_is_bracket(items, j):
        return True
    return (_next_is_bracket(items, j, through_stop=True) and len(WORD.findall(ETC.sub(" ", text_of(items[i:j])))) >= 3
            and not _dotted_citation(items, i, j))


def tag_latin(e, decisions: list, unit: str, in_note: bool = False) -> None:
    if e.get("ana") == "foreign":
        # a passage already: but Burton's notes inside it are his own matter, read on their own (2026-11-18: "Haec
        # comice dicta cave ne male capias", a note in the Latin poem Ad librum, was never tagged or translated)
        for n in e.iter(T("note")):
            if not any(a.tag == T("note") for a in n.iterancestors()):
                tag_latin(n, decisions, unit, in_note=True)
        return
    if e.tag in (ED("trans"), ED("verse-trans"), ED("block"), T("foreign"), T("supplied")):
        return
    if e.get("facs") is not None:  # our own transcriptions of heading images are not source text
        return
    in_note = in_note or e.tag == T("note")
    items = _alternate(take_items(e))
    out, last = [], 0
    queue = _runs(items)
    cite_pieces: set[tuple[int, int]] = set()  # pieces of a run that was a reference as a whole
    while queue:
        i, j = queue.pop(0)
        text = text_of(items[i:j])
        bracket = _bracketed(items, i, j)
        verdict, conf, why = classify(text, bracket, in_note, _stop_after(items, j) and not bracket)
        if (i, j) in cite_pieces and verdict == "la" and not _strong_latin(text):
            # cut out of a reference ("…folly. Vide Isaacum Pontanum descript. …"): Latin only on strong evidence
            verdict, conf, why = "citation", "medium", "a piece of a reference run, weak Latin evidence"
        if not bracket and _dotted_citation(items, i, j):
            verdict, conf, why = ("citation", "medium",
                                  "short fragments separated by full stops (e.g. 'Donat. vita. ejus')")
        elif not bracket and re.fullmatch(r"\s*\p{Lu}?\p{Ll}+-\p{Ll}+\s*", text):
            verdict, conf, why = "en", "medium", "hyphenated compound (an English loan-word, e.g. 'Bona-roba')"
        elif verdict != "la" and (pieces := _resplit(items, i, j, verdict, in_note)):
            if verdict == "citation":
                cite_pieces.update(pieces)
            queue[:0] = pieces  # each piece is classified on its own
            continue
        if verdict != "la" and bracket and j - i > 1:
            # a Gowland bracket follows: the Latin may be only the run's last fragments
            for k in range(j - 1, i, -1):
                if not _is_italic(items[k]):
                    continue
                v2, c2, w2 = classify(text_of(items[k:j]), True, in_note)
                if v2 == "la":
                    decisions.append({"unit": unit, "text": text_of(items[i:k]), "verdict": verdict,
                                      "confidence": conf, "why": why + " (prefix of a split run)",
                                      "in_note": in_note})
                    out.extend(items[last:k])
                    i, text, verdict, conf, why = k, text_of(items[k:j]), v2, c2, w2 + " (suffix of a split run)"
                    last = k
                    break
        lang, resp = "la", "#rules"
        if verdict in ("undetermined", "name") or (not bracket and verdict in ("la", "en") and thin(text, why)):
            # the rules cannot decide: use the model's ruling if there is one (machine layer, labelled)
            adj = adjudicated(unit, text)
            if adj and adj["confidence"] == "low":
                adj = None  # the model was unsure: leave the rules' verdict and keep it for review
            if re.fullmatch(r"\s*&c\.?\s*", text):
                adj = None  # "&c" alone is "etc.": not a passage to translate
                verdict, why = "en", "&c alone (etc.)"
            if adj and adj["label"] in MODEL_LANGS and adj["kind"] == "title":
                # a book's title cited as a source is a reference, though its words are Latin (LABELLING.md; V5's
                # fifth cycle: "de rebus caelestibus", ruled la/title, had become a passage)
                verdict, why = "citation", f"model ruling ({adj['model']}/{adj['prompt']}): {adj['label']} title"
            elif adj and adj["label"] in MODEL_LANGS:
                verdict, lang, resp = "la", adj["label"], "#model"
                if lang == "grc" and not re.search(r"\p{Script=Greek}", text):
                    lang = "grc-Latn"  # Greek written in Latin letters (e.g. Aristophanes' frogs)
                if lang == "he" and not re.search(r"\p{Script=Hebrew}", text):
                    lang = "he-Latn"  # Hebrew written in Latin letters
                conf = "medium" if adj["confidence"] == "high" else adj["confidence"]
                why = f"model ruling ({adj['model']}/{adj['prompt']}): {adj['label']} {adj['kind']}"
            elif adj:
                verdict, why = adj["label"], f"model ruling ({adj['model']}/{adj['prompt']}): {adj['label']}"
        # a reference run holding Latin words: the model's ruling may find a Latin sentence in it (V5's fifth cycle)
        if verdict == "citation" and resp == "#rules" and not why.startswith("model ruling") \
                and latin_content(text) >= 2 and (adj := _ruling(unit, text)):
            mwhy = f"model ruling ({adj['model']}/{adj['prompt']}): {adj['label']}"
            rng = None
            if _latin_ruling(adj):
                rng = _shed(items, i, j, in_note)
                if rng == (i, j):
                    verdict, lang, resp, conf, why = "la", _model_lang(adj, text), "#model", "medium", mwhy
                    rng = None
            elif adj["label"] == "mixed":
                rng = _part_range(items, i, j, adj["foreign_part"])
            if rng:
                k, m = rng
                decisions.append({"unit": unit, "text": text, "verdict": "citation", "confidence": conf,
                                  "why": mwhy + "; its Latin part tagged", "in_note": in_note})
                decisions.append({"unit": unit, "text": text_of(items[k:m]), "verdict": "la", "confidence": "medium",
                                  "why": mwhy + " (the Latin part of a reference run)", "in_note": in_note})
                out.extend(items[last:k])
                lg = _model_lang(adj, text) if adj["label"] in MODEL_LANGS else "la"
                f = el("foreign", {"lang-tmp": lg, "resp": "#model", "cert": "medium", "ana": "foreign"})
                put_items(f, items[k:m])
                out.append(f)
                out.extend(items[m:j])
                last = j
                continue
        i_run = i
        if verdict == "la" and j - i > 1 and resp == "#rules":
            j_run = j
            i, j = _trim_run(items, i, j, in_note, bracket)
            text = text_of(items[i:j])
            # trimmed to a short run on thin evidence ("Panormitan. rebus gestis Alph" -> "rebus gestis Alph"): the
            # model's ruling on the trimmed run decides, as above (2026-11-20)
            if not bracket and thin(text, why) and (adj := adjudicated(unit, text)) and adj["confidence"] != "low" \
                    and adj["label"] not in MODEL_LANGS:
                verdict, why = adj["label"], f"model ruling ({adj['model']}/{adj['prompt']}): {adj['label']}"
            # what the trim cut off may itself be Latin ("Elvarum choreas Olaus lib. 3. vocat. Saltum adeo…")
            if verdict == "la":
                if i > i_run and (new_i := _regain(items, unit, i_run, i - 1, True, decisions, in_note)) is not None:
                    i, resp, why = new_i, "#model", why + "; a cut piece joined by model ruling"
                if j < j_run and (new_j := _regain(items, unit, j + 1, j_run, False, decisions, in_note)) is not None:
                    j, resp, why = new_j, "#model", why + "; a cut piece joined by model ruling"
                text = text_of(items[i:j])
        if verdict == "la" and resp == "#rules" and (tw := _title_after(items, i_run, i, j, bracket)):
            verdict, conf, why = "citation", "medium", tw
            for k in range(i, j, 2):
                items[k].set("lang-title", "1")  # the bracket pass must not take it back (removed by finalize_lang)
        if verdict == "en" and resp == "#rules" and not why.startswith("model ruling"):
            for k in range(i, j, 2):
                if mx := _wrap_mixed(items[k], in_note):
                    decisions.append({"unit": unit, "text": mx, "verdict": "la", "confidence": "medium",
                                      "why": "a Latin clause inside an English italic run", "in_note": in_note})
        decisions.append({"unit": unit, "text": text, "verdict": verdict, "confidence": conf, "why": why,
                          "in_note": in_note})
        out.extend(items[last:i])
        if verdict == "la":
            f = el("foreign", {"lang-tmp": lang, "resp": resp, "cert": conf, "ana": "foreign"})
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


MODEL_LANGS = {"la", "grc", "it", "fr", "es", "de", "nl", "enm", "he"}

# 2026-11-20, V5's fourth cycle (owner: "just do the remainder of V5 yourself"): three cycles of rule changes on fresh
# rounds stopped at P 0.95-0.96, R 0.94-0.97, nearly every error a short run the rules decided on one or two lexicon
# hits ("Genius" and "per annum" as Latin because Burton's Latin has the words; "inquis" as English). Such a run, of
# three words or fewer with no Gowland bracket to confirm it, now takes the model's ruling (prompt la-v2, labelled
# resp="#model"); a low-confidence ruling still leaves the rules' verdict.
THIN_WHY = re.compile(r"(?:no function words; lexicon )?la=(\d) en=(\d)|"
                      r"(?:capitalised term|sidenote run) attested in Burton's Latin \(lexicon la=(\d)\)")


def thin(text: str, why: str) -> bool:
    """A short run decided on one or two lexicon hits."""
    m = THIN_WHY.fullmatch(why)
    if not m or len(WORD.findall(text)) > 3:
        return False
    hits = sum(int(x) for x in m.groups() if x)
    return 0 < hits <= 2


# 2026-11-20, V5's fifth cycle: the errors left on the fresh round h6 sat on the line between a reference and Latin. A
# Latin sentence inside a reference run ("Elvarum choreas Olaus lib. 3. vocat", "Herodotus lib. 2 Euterpe: Uxores
# insignium virorum…") was left a citation, or cut off a Latin run by the trim and never recorded; a roman preposition
# before a Latin word ("in secundis") stayed outside the passage. Each such run now takes the model's ruling (la-v2,
# resp="#model"); without a ruling, or with a low one, the rules' verdict stands.
def latin_content(text: str) -> int:
    """Latin content words of a run: lowercase, >= 4 letters, attested in Burton's Latin, not an abbreviation."""
    return sum(1 for w in WORD.findall(text) if len(w) >= 4 and w[0].islower() and w.lower() not in ABBREV
               and lexicon.latinness(w) == "la")


def _ruling(unit: str, text: str) -> dict | None:
    adj = adjudicated(unit, text)
    return adj if adj and adj["confidence"] != "low" else None


def _model_lang(adj: dict, text: str) -> str:
    lang = adj["label"]
    if lang == "grc" and not re.search(r"\p{Script=Greek}", text):
        return "grc-Latn"
    if lang == "he" and not re.search(r"\p{Script=Hebrew}", text):
        return "he-Latn"
    return lang


def _part_range(items: list, s: int, e: int, part: str | None) -> tuple[int, int] | None:
    """The items [k, l) of the run items[s:e] whose text is exactly `part` (whole italic fragments only)."""
    want = " ".join((part or "").split()).strip(" ,.;:")
    if not want:
        return None
    for k in range(s, e, 2):
        for m in range(k + 1, e + 1, 2):
            got = " ".join(text_of(items[k:m]).split()).strip(" ,.;:")
            if got == want:
                return k, m
            if len(got) > len(want):
                break
    return None


def _latin_ruling(adj: dict | None) -> bool:
    """A ruling that makes a reference run (or a piece cut off one) Latin: a language, and not a title or a reference
    (LABELLING.md: a book's title cited as a source is `citation`, though its words are Latin)."""
    return bool(adj) and adj["label"] in MODEL_LANGS and adj["kind"] not in ("title", "citation")


def _shed(items: list, s: int, e: int, in_note: bool) -> tuple[int, int]:
    """Leading and trailing reference fragments ("Danaeus lib. 3 de sortiariis, | Vidi, inquit…"; "…animi (Felix
    Plater lib. 3 | de alienat. mentis") shed from a run the model ruled Latin as a whole: fragments that are
    citation-like and hold fewer than two Latin content words. At least one fragment is kept."""
    while e - s > 1 and latin_content(text_of([items[s]])) < 2 and _citation_like(items, s, in_note):
        s += 2
    while e - s > 1 and latin_content(text_of([items[e - 1]])) < 2 and _citation_like(items, e - 1, in_note):
        e -= 2
    return s, e


def _regain(items: list, unit: str, s: int, e: int, at_end: bool, decisions: list, in_note: bool) -> int | None:
    """Fragments items[s:e] that the trim cut off a Latin run: if they hold Latin words, the model's ruling may join
    them (all, or the part next to the run) back to it. Returns the run's new start (at_end: the cut piece precedes
    the run) or new end, or None."""
    ctext = text_of(items[s:e])
    if latin_content(ctext) < 2:
        return None
    adj = _ruling(unit, ctext)
    new, verdict, why = None, "citation", "cut from a Latin run by the rules (a reference with Latin words)"
    if _latin_ruling(adj):
        a, b = _shed(items, s, e, in_note)
        if (b == e) if at_end else (a == s):  # the Latin must still touch the run
            new, verdict = (a if at_end else b), "la"
    elif adj and adj["label"] == "mixed" and (rng := _part_range(items, s, e, adj["foreign_part"])):
        if (rng[1] == e) if at_end else (rng[0] == s):
            new, verdict = (rng[0] if at_end else rng[1]), "mixed"
    if adj:
        why = f"model ruling ({adj['model']}/{adj['prompt']}): {adj['label']}" + \
            ("; joined to the Latin run" if new is not None else "")
    decisions.append({"unit": unit, "text": ctext, "verdict": verdict, "confidence": "medium", "why": why,
                      "in_note": in_note})
    return new


def _plain(x) -> str:
    """Burton's text of an item: Gowland's matter and sidenotes count for nothing."""
    if isinstance(x, str):
        return x
    if x.tag in (T("note"), ED("trans"), ED("verse-trans"), ED("block")) or \
            (x.tag == T("supplied") and x.get("resp") == "#gowland"):
        return ""
    return text_of([x])


def tag_before_unattached_brackets(div, decisions: list, unit: str) -> None:
    """Gowland translated nearly everything he judged foreign. Where one of his brackets follows no passage (V5's
    census, 2026-11-20: 96 of 4,345), the clause before it takes the model's ruling, which sees Burton's text only,
    never Gowland's words. A ruling of Latin (or the foreign part of a mixed one) is wrapped as a passage when it
    begins and ends on whole fragments; otherwise the rules' text is left as it is and the decision says why."""
    from . import gowland

    for t in gowland.trans_without_foreign(div):
        parent = t.getparent()
        items = take_items(parent)
        idx = next(k for k, x in enumerate(items) if x is t)
        a = idx
        while a > 0 and not (not isinstance(items[a - 1], str) and (
                items[a - 1].tag in (ED("trans"), ED("verse-trans"), ED("block"), T("foreign"), T("lb"))
                or items[a - 1].get("ana") == "foreign")):
            a -= 1
        texts = [_plain(x) for x in items[a:idx]]
        s = "".join(texts)
        clause = re.split(r"[;:()!?]|(?<=\p{Ll})\.\s", s.rstrip())[-1].strip(" ,")
        in_note = any(x.tag == T("note") for x in t.iterancestors())
        if len(WORD.findall(clause)) < 1:
            put_items(parent, items)
            continue
        adj = _ruling(unit, clause)
        part = None
        if _latin_ruling(adj):
            part = clause
        elif adj and adj["label"] == "mixed" and adj["foreign_part"] and \
                " ".join(adj["foreign_part"].split()) in " ".join(clause.split()):
            part = adj["foreign_part"]
        why = "text before an unattached Gowland bracket" + \
            (f"; model ruling ({adj['model']}/{adj['prompt']}): {adj['label']}" if adj else " (no ruling)")
        if part:
            part = part.strip(" .,;:").lstrip("0123456789 .,")
            words = [w for w in WORD.findall(ETC.sub(" ", part)) if len(w) >= 3]
            # the conventions (LABELLING.md): "&c" alone is "etc."; a title ("de Anima") is a reference; a list of
            # Latin-form names ("Carolus Sapiens, Philippus Bonus") is names
            if not words:
                part, why = None, why + "; not a passage (no word)"
            elif re.match(r"[Dd]e\s", part) and len(words) <= 6:
                part, why = None, why + "; a title (de …), a reference"
            elif len(words) >= 2 and all(w[0].isupper() for w in words):
                part, why = None, why + "; capitalised words only (names)"
        placed = None
        if part:
            pat = r"\s+".join(map(re.escape, part.split()))
            hits = list(re.finditer(pat, s))
            if hits:
                placed = _wrap_span(items, a, texts, hits[-1].start(), hits[-1].end(),
                                    _model_lang(adj, part) if adj["label"] in MODEL_LANGS else "la")
        if placed is not None:
            items = placed
            decisions.append({"unit": unit, "text": " ".join(part.split()), "verdict": "la", "confidence": "medium",
                              "why": why + "; tagged", "in_note": in_note})
        else:
            decisions.append({"unit": unit, "text": " ".join(clause.split()),
                              "verdict": "undetermined" if not adj else ("la" if part else adj["label"]),
                              "confidence": "low" if not adj else "medium", "in_note": in_note,
                              "why": why + ("; not placed (it does not begin and end on whole fragments)" if part
                                            else "")})
        put_items(parent, items)


def _wrap_span(items: list, a: int, texts: list[str], cs: int, ce: int, lang: str) -> list | None:
    """Wrap the characters [cs, ce) of the items from a on (whose texts are `texts`) in a passage. A boundary may
    split a string, but not an element. Returns the new item list, or None."""
    pos, first, last = 0, None, None
    for k, tx in enumerate(texts):
        start, end = pos, pos + len(tx)
        x = items[a + k]
        if start <= cs and ce <= end and not isinstance(x, str) and x.tag == T("hi") and not len(x) \
                and x.text == tx and (cs, ce) != (start, end):
            # the whole stretch inside one italic fragment: wrap it inside the fragment (markup only)
            f = el("foreign", {"lang-tmp": lang, "resp": "#model", "cert": "medium", "ana": "foreign"})
            f.text, f.tail = tx[cs - start:ce - start], tx[ce - start:] or None
            x.text = tx[:cs - start] or None
            x.append(f)
            return items
        if first is None and cs < end:
            if not isinstance(items[a + k], str) and cs != start:
                return None
            first = (a + k, cs - start)
        if first is not None and ce <= end:
            if not isinstance(items[a + k], str) and ce != end:
                return None
            last = (a + k, ce - start)
            break
        pos = end
    if first is None or last is None:
        return None
    (i, io), (j, jo) = first, last
    inner = []
    for k in range(i, j + 1):
        x = items[k]
        if isinstance(x, str):
            lo = io if k == i else 0
            hi = jo if k == j else len(x)
            inner.append(x[lo:hi])
        else:
            inner.append(x)
    f = el("foreign", {"lang-tmp": lang, "resp": "#model", "cert": "medium", "ana": "foreign"})
    put_items(f, inner)
    before = [items[i][:io]] if isinstance(items[i], str) else []
    after = [items[j][jo:]] if isinstance(items[j], str) else []
    return items[:i] + before + [f] + after + items[j + 1:]


ROMAN_PREP = re.compile(r"(?<![\p{L}\p{M}’'])(in|ad|a|de|ex|e|cum|pro|per|sine|apud|sub|inter|ob)\s$")


def join_roman_prepositions(div, decisions: list, unit: str) -> None:
    """A roman Latin preposition directly before a Latin passage ("to be in *secundis*"): the model's ruling on the
    two together decides whether it belongs to the Latin; if so it joins the passage (markup only)."""
    for f in list(div.iter(T("foreign"))):
        if f.get("ana") != "foreign" or (f.get("lang-tmp") or f.get(XML_LANG)) != "la":
            continue
        p = f.getprevious()
        holder = (p.tail if p is not None else f.getparent().text) or ""
        m = ROMAN_PREP.search(holder)
        if not m:
            continue
        text = f"{m.group(1)} {text_of([f]).strip()}"
        in_note = any(a.tag == T("note") for a in f.iterancestors())
        adj = _ruling(unit, text)
        if adj and adj["label"] == "la":
            rest = holder[:m.start()]
            if p is not None:
                p.tail = rest
            else:
                f.getparent().text = rest
            f.text = m.group(0) + (f.text or "")
            f.set("resp", "#model")
            decisions.append({"unit": unit, "text": text, "verdict": "la", "confidence": "medium", "in_note": in_note,
                              "why": f"a roman word before a Latin passage; model ruling ({adj['model']}/"
                                     f"{adj['prompt']}): la, joined"})
        else:
            decisions.append({"unit": unit, "text": text, "verdict": "en", "confidence": "medium", "in_note": in_note,
                              "why": "a roman word before a Latin passage" +
                                     (f"; model ruling ({adj['model']}/{adj['prompt']}): {adj['label']}" if adj
                                      else " (no ruling)")})

# 2026-11-18, after held-out h3: a Latin title in the running text ("Prosper Calanius in his book de atra bile",
# "in a consultation of his pro hypocondriaco") or after an author or a title abbreviation in a note ("Tr. de morbis
# amentium") is a citation, not quoted Latin (LABELLING.md: titles used as references are `citation`).
TITLE_OPENERS = {"de", "pro", "contra", "adversus"}
TITLE_BEFORE = re.compile(r"\b(?:books?|tracts?|treatises?|homil(?:y|ies)|dialogues?|volumes?|consultations?"
                          r"|commentar(?:y|ies)|comments?|epistles?|orations?|sermons?|discourses?|lectures?|chap)\b"
                          r"\.?(?:\s+of\s+his)?\s*,?\s*(?:\([^()]{0,40}\)\s*,?\s*)?$", re.I)
TITLE_ABBREV = {"tr", "tract", "lib", "com", "comment", "syntag", "dial", "orat", "serm", "epist", "hom", "exercit",
                "disp", "quaest", "praefat", "praef"}


def _title_after(items: list, i_run: int, i: int, j: int, bracket: bool) -> str | None:
    """Why the Latin run items[i:j] is a book's title, or None. `i_run`: where the run began before leading
    author or title fragments were shed. After a title noun ("in his book") even a bracketed run is a title
    (Gowland translates titles too); after a shed author or abbreviation only an unbracketed one is."""
    words = WORD.findall(ETC.sub(" ", text_of(items[i:j])))
    if not words or words[0].lower() not in TITLE_OPENERS or len(words) > 7:
        return None
    if i == i_run:
        before = items[i - 1] if i > 0 and isinstance(items[i - 1], str) else ""
        if TITLE_BEFORE.search(before):
            return f"a title after {before.strip()[-24:]!r}"
        return None
    if bracket:
        return None
    last = text_of([items[i - 2]]).strip()
    lw = WORD.findall(last)
    if lw and (lw[-1].lower() in TITLE_ABBREV or (_capitalised(last) and not re.search(r"\d", last))):
        return f"a title after the author or abbreviation {last[-24:]!r}"
    return None


def _strong_latin(t: str) -> bool:
    """>= 5 words, >= 3 of them Latin function words or endings."""
    words = [w.lower() for w in WORD.findall(ETC.sub(" ", t))]
    return len(words) >= 5 and sum(w in LA_FUNCTION or bool(LA_ENDINGS.search(w)) for w in words) >= 3


def _english_words(t: str) -> int:
    return sum(w in EN_FUNCTION and w not in EN_LATIN_AMBIGUOUS and w not in LA_FUNCTION
               for w in (x.lower().strip("’'") for x in WORD.findall(t)))


def _wrap_mixed(h, in_note: bool) -> str | None:
    """An English italic element that ends or begins with a Latin clause ("…what shall I do? Vos O dii Averrunci,
    solvite me his curis"; "si cerebrum sit calidius, if the brain be hot…"): wrap the Latin part in a passage
    inside the element (markup only; the text is unchanged). The Latin part has >= 3 words, is Latin by the rules
    and holds no English word; the English part holds >= 2 English words. Returns the Latin text, or None."""
    if not _is_italic(h) or h.get("rend") != "i" or len(h) or not h.text:
        return None
    s = h.text

    def latin(t):
        t = t.strip()
        words = WORD.findall(ETC.sub(" ", t))
        if len(words) < 3 or _english_words(t) or classify(t, False, in_note)[0] != "la":
            return False
        n_la = sum(w.lower() in LA_FUNCTION or bool(LA_ENDINGS.search(w.lower())) for w in words)
        lex = [lexicon.latinness(w) for w in words if len(w) >= 3]
        # strong evidence only: a clause cut out of English ("Good Lord deliver me" is not Latin for its "me")
        return (n_la >= 2 and lex.count("en") <= lex.count("la")) or (lex.count("la") >= 3 and not lex.count("en"))

    cuts = [m.end() for m in re.finditer(r"[,;:?!]\s+", s)]
    span = next(((c, len(s)) for c in cuts if latin(s[c:]) and _english_words(s[:c]) >= 2), None)
    if span is None:
        span = next(((0, c) for c in reversed(cuts) if latin(s[:c]) and _english_words(s[c:]) >= 2), None)
    if span is None:
        return None
    a, b = span
    b = a + len(s[a:b].rstrip(" ,;:."))
    f = el("foreign", {"lang-tmp": "la", "resp": "#rules", "cert": "medium", "ana": "foreign"})
    f.text, f.tail = s[a:b], s[b:] or None
    if a == 0:
        h.text = None
        h.insert(0, f)
    else:
        h.text = s[:a]
        h.append(f)
    return f.text


def adjudicated(unit: str, text: str) -> dict | None:
    from ..translate import adjudicate  # the layer file only; no model call happens during ingest

    return adjudicate.lookup(unit, text)


def correct_languages(div, unit: str, stats) -> None:
    """Where the model ruled that a Latin-tagged passage is really another language, relabel it."""
    from ..textview import public_text

    for e in div.iter():
        if isinstance(e.tag, str) and e.get("ana") == "foreign" and e.get(XML_LANG) == "la":
            adj = adjudicated(unit, public_text(e))
            if adj and adj["label"] in MODEL_LANGS - {"la"}:
                e.set(XML_LANG, adj["label"])
                e.set("resp", "#model")
                stats[f"relabelled:{adj['label']}"] += 1


def _dotted_citation(items: list, i: int, j: int) -> bool:
    """A run made only of short fragments joined by full stops: an abbreviated reference."""
    members = list(range(i, j, 2))
    seps = [items[k] for k in range(i + 1, j, 2)]
    after = items[j] if j < len(items) and isinstance(items[j], str) else ""
    return (len(members) >= 2 and all(len(WORD.findall(text_of([items[m]]))) <= 2 for m in members)
            and all(s.lstrip().startswith(".") for s in seps) and (after.lstrip().startswith((".", ",")) or not after))


def _sentence_break(items: list, k: int) -> bool:
    """Between run members k and k + 2: a fragment of >= 3 words that does not end in an abbreviation,
    a full stop, and a capitalised fragment ("…and all night. Quae quidem")."""
    sep, nxt = items[k + 1], text_of([items[k + 2]]).lstrip()
    words = WORD.findall(text_of([items[k]]))
    return (sep.strip().startswith(".") and len(words) >= 3 and words[-1].lower() not in ABBREV
            and nxt[:1].isupper())


def _stop_after(items: list, j: int) -> bool:
    return j < len(items) and isinstance(items[j], str) and items[j].lstrip().startswith(".")


def _resplit(items: list, i: int, j: int, verdict: str, in_note: bool) -> list[tuple[int, int]] | None:
    """A multi-fragment run that is not Latin as a whole may still hold a Latin passage:
    * before a Gowland bracket, behind leading citation or name fragments ("Hoc fere Zanchius com. in 4
      cap. ad Ephes. Aequissimam vocat usuram…"). Without a bracket the rest is usually a title
      ("Lib. de vita longa"), so the rule needs the bracket;
    * in a run judged English, after a sentence break ("…and all night. Quae quidem").
    Returns the pieces to classify on their own, or None."""
    if j - i <= 1:
        return None
    bracket = _bracketed(items, i, j)
    if bracket:
        a = i
        while j - a > 1 and items[a + 1] != "" and _citation_like(items, a, in_note):
            a += 2
        rest = text_of(items[a:j])
        if a > i and len(WORD.findall(rest)) >= 3 and classify(rest, True, in_note)[0] == "la":
            return [(i, a - 1), (a, j)]
    if verdict not in ("en", "citation"):
        return None
    cuts = [k for k in range(i, j - 2, 2) if _sentence_break(items, k)]
    if not cuts:
        return None
    bounds = list(zip([i, *[k + 2 for k in cuts]], [*[k + 1 for k in cuts], j], strict=True))
    verdicts = [classify(text_of(items[s:e]), e == j and bracket, in_note, _stop_after(items, e))[0]
                if len(WORD.findall(text_of(items[s:e]))) >= 2 else None for s, e in bounds]
    # a citation run may hold a whole English sentence before the reference ("…if cold, folly. David Crusius
    # Theat. morb. … lib. 2"): split it so the sentence is read on its own (2026-11-18)
    if "la" in verdicts or (verdict == "citation" and "en" in verdicts):
        return bounds
    return None


def _citation_like(items: list, k: int, in_note: bool) -> bool:
    """A run member that is a citation fragment or a bare name, judged with the separator after it."""
    t = text_of([items[k]]).strip()
    sep = items[k + 1] if k + 1 < len(items) and isinstance(items[k + 1], str) else ""
    words = WORD.findall(t)
    stopped = t + "." if sep.lstrip().startswith(".") else t
    if not words or CITATION.search(stopped) or WORK_TITLE.match(stopped):
        return True
    if t.endswith("&c"):  # "&c." is "etc.", not the citation abbreviation "c."
        return classify(t, False, in_note)[0] in ("citation", "name")
    if sep.lstrip().startswith(".") and ((words[-1].lower() in ABBREV and len(words) <= 3)
                                         or (len(words) == 1 and len(t) <= 9)):
        return True  # an abbreviation: "Path.", "Institut.", "expedit." (a one-word fragment before a stop)
    return classify(t, False, in_note)[0] in ("citation", "name")


def _trim_run(items: list, i: int, j: int, in_note: bool, bracket: bool = False) -> tuple[int, int]:
    """Shed leading citation/name fragments ("Eobanus Hessus. Quibus omnis…") and a trailing name that
    starts Burton's English sentence ("…meliores, Sparta had many better men"). The trimmed run is used
    only if it is still Latin, and (before a bracket, which translates the whole run) still holds a word
    of >= 3 letters: "Perseus P. Consuli. S. [Perseus to Paullus the consul, greetings]" is not trimmed
    to "S"."""
    a, b = i, j
    while b - a > 1 and items[a + 1] != "" and _citation_like(items, a, in_note):
        a += 2  # never cut where markup splits a word ("Si dominus 7" + "mae")
    tail = items[b] if b < len(items) and isinstance(items[b], str) else ""
    while b - a > 1 and re.match(r"\s+\p{Ll}", tail):
        last = text_of([items[b - 1]]).strip()
        if len(WORD.findall(last)) == 1 and last[:1].isupper():
            b -= 2
            tail = " x"
        else:
            break
    rest = text_of(items[a:b])
    if bracket and not any(len(w) >= 3 for w in WORD.findall(ETC.sub(" ", rest))):
        return i, j
    if (a, b) != (i, j) and classify(rest, bracket and b == j, in_note)[0] == "la":
        return a, b
    return i, j


ROMAN_SKIP = None  # filled lazily: element tags whose text the roman-run scan must not touch


def _roman_spans(text: str) -> list[tuple[int, int, int, int]]:
    """(start, end, latin, other) of runs of roman Latin in a string: >= 3 Latin words, no English word,
    >= 60 % Latin. Latin = attested in Burton's Latin (lexicon), a Latin function word or ending."""
    spans, cur = [], None
    for m in ROMAN_TOKEN.finditer(text):
        w = m.group(0)
        if not re.match(r"[\p{L}&]", w):
            if any(ch in CLAUSE_STOP for ch in w) and cur:
                spans.append(cur)
                cur = None
            continue
        low = w.lower()
        is_la = w == "&" or low in LA_FUNCTION or lexicon.latinness(w) == "la" or \
            (bool(LA_ENDINGS.search(low)) and lexicon.latinness(w) != "en")
        is_en = lexicon.latinness(w) == "en" or (low in EN_FUNCTION and low not in EN_LATIN_AMBIGUOUS
                                                  and low not in LA_FUNCTION)
        if is_en and not is_la:
            if cur:
                spans.append(cur)
            cur = None
            continue
        if cur is None:
            if not is_la:
                continue
            cur = [m.start(), m.end(), 0, 0]
        cur[1] = m.end()
        cur[2 if is_la else 3] += 1
    if cur:
        spans.append(cur)
    out = []
    for s, e, la, other in spans:
        # trim trailing non-Latin words (unknowns at the end are more likely English names)
        if la >= 3 and la >= 0.6 * (la + other):
            out.append((s, e, la, other))
    return out


def tag_roman_runs(div, decisions: list, unit: str) -> None:
    """Roman-type Latin anywhere (not only before a bracket), e.g. a whole Latin sentence in a sidenote."""
    skip = (T("hi"), T("foreign"), ED("trans"), ED("verse-trans"), ED("block"), T("supplied"), T("head"),
            ED("enref"), T("pb"), T("lb"), T("choice"))

    def visit(e):
        if e.tag in skip or e.get("ana") == "foreign" or (e.get(XML_LANG) or "en") != "en" or e.get("facs"):
            return
        in_note = e.tag == T("note") or any(a.tag == T("note") for a in e.iterancestors())
        items = take_items(e)
        out = []
        for it in items:
            if not isinstance(it, str):
                out.append(it)
                continue
            pos = 0
            for s, t, la, other in _roman_spans(it):
                out.append(it[pos:s])
                f = el("foreign", {"lang-tmp": "la", "resp": "#rules", "cert": "medium", "ana": "foreign"})
                f.text = it[s:t]
                out.append(f)
                decisions.append({"unit": unit, "text": it[s:t], "verdict": "la", "confidence": "medium",
                                  "why": f"roman Latin run; la={la} other={other}", "in_note": in_note})
                pos = t
            out.append(it[pos:])
        put_items(e, out)
        for c in list(e):
            if isinstance(c.tag, str) and c.get("lang-tmp") is None:
                visit(c)

    visit(div)


def _italic_text(e) -> str:
    return "".join(text_of([h]) for h in e.iter(T("hi"))
                   if h.get("rend") == "i" and not any(x.tag == T("note") for x in h.iterancestors()))


def _n_letters(s: str) -> int:
    return len(re.findall(r"\p{L}", s))


def tag_chaucer(div, stats) -> None:
    """The EPUB sets Chaucer in `span.lucida` (SURVEY): Middle English in Gowland's modernised spelling.
    Tagged `enm` for language only (no ana="foreign": it gets glosses, never a translation)."""
    for h in list(div.iter(T("hi"))):
        if h.get("rend") != "lucida" or h.getparent().tag == T("foreign"):
            continue
        f = el("foreign", {XML_LANG: "enm", "resp": "#rules", "cert": "high"})
        h.addprevious(f)
        f.tail, h.tail = h.tail, None
        f.append(h)
        stats["script:enm"] += 1


def split_english_tail(div, stats) -> None:
    """A verse group whose italic Latin lines are followed, in the same group, by roman English lines
    (3.2.5.1: "facilis descensus Averni; …" then "It is an easy passage down to hell, …") is two
    groups in substance: the trailing lines become Burton's own `translation-block`. Markup only."""
    for lg in list(div.iter(T("lg"))):
        if lg.get("ana") == "foreign" or lg.get("type") == "translation-block" or \
                lg.getparent().tag == ED("verse-trans"):
            continue
        lines = lg.findall(T("l"))
        if len(lines) < 2 or len(lines) != len([k for k in lg if isinstance(k.tag, str)]):
            continue
        ital = [_n_letters(_italic_text(ln)) >= 0.75 * max(1, _n_letters(text_of([ln]))) for ln in lines]
        k = ital.index(False) if False in ital else len(lines)
        if k == 0 or k == len(lines) or any(ital[k:]):
            continue
        la, _, _ = classify(" ".join(text_of([ln]) for ln in lines[:k]), True)
        en, conf, _ = classify(" ".join(text_of([ln]) for ln in lines[k:]), False)
        if la != "la" or en != "en" or conf != "high":
            continue
        tail = el("lg", {"type": "translation-block"})
        lg.addnext(tail)
        tail.tail, lg.tail = lg.tail, None
        for ln in lines[k:]:
            tail.append(ln)
        stats["lg:english-tail-split"] += 1


def tag_verse_latin(div, decisions: list, unit: str) -> None:
    """Verse groups followed by a translation group and made of Latin italics: lg-level Latin.
    The italics decide only where they cover most of the group: in Burton's English verse the
    italics are often just Latin names ("Wanton Propertius, and witty Gallus")."""
    for q in div.iter(T("quote")):
        kids = [k for k in q if isinstance(k.tag, str)]
        for a, b in zip(kids, kids[1:], strict=False):
            if a.tag != T("lg") or a.get("ana") == "foreign":
                continue
            followed = b.tag == ED("verse-trans") or b.get("type") == "translation-block"
            text = text_of([a])
            ital = _italic_text(a)
            if _n_letters(ital) < 0.75 * _n_letters(text):
                ital = ""
            verdict, conf, why = classify(ital or text, followed)
            if followed and verdict == "la":
                a.set(XML_LANG, "la")
                a.set("ana", "foreign")
                a.set("resp", "#rules")
                a.set("cert", conf)
                decisions.append({"unit": unit, "text": text.strip(), "verdict": "la", "confidence": conf,
                                  "why": "verse group followed by translation; " + why})


def finalize_lang(div) -> None:
    for e in div.iter(T("hi")):
        e.attrib.pop("lang-title", None)
    for f in div.iter(T("foreign")):
        if "lang-tmp" in f.attrib:  # set by the rules; manual/fix foreign elements carry xml:lang already
            f.set(XML_LANG, f.attrib.pop("lang-tmp"))


def run(div, unit: str, stats, *, gowland_unit: bool = False) -> list[dict]:
    decisions: list[dict] = []
    if gowland_unit:  # a whole page of Gowland's: tag scripts only, never make passages
        _wrap_script_runs(div, stats, gowland=True)
        finalize_lang(div)
        return decisions
    tag_verse_groups(div, stats)
    _wrap_script_runs(div, stats)
    tag_chaucer(div, stats)
    split_english_tail(div, stats)
    tag_verse_latin(div, decisions, unit)
    tag_latin(div, decisions, unit)
    tag_roman_before_brackets(div, decisions, unit)
    tag_roman_runs(div, decisions, unit)
    join_roman_prepositions(div, decisions, unit)
    tag_before_unattached_brackets(div, decisions, unit)
    from . import census_apply  # V5 by census (D13): the judge's rulings, a labelled machine layer

    census_apply.apply(div, decisions, unit)
    finalize_lang(div)
    correct_languages(div, unit, stats)
    for d in decisions:
        stats[f"italic-run:{d['verdict']}"] += 1
    return decisions


def is_foreign(x) -> bool:
    return not isinstance(x, str) and (local(x.tag) == "foreign" or x.get("ana") == "foreign")
