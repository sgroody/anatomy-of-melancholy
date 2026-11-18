"""Language identification, M1 rules (SPEC §6.1, steps 1-4).

Deterministic script tagging for Greek, Hebrew and Arabic; rule-based Latin detection over
italic runs using English/Latin function words, Latin endings and Gowland's brackets as context.
No language-detector library is used. Every decision records its confidence and method.
"""

import regex as re

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
""".split())
LA_ENDINGS = re.compile(r"(?:orum|arum|ibus|ntur|tur|bant|bunt|erunt|isse|iis|ae|um|que|ii|ium)$")
# "&c." is "etc.", not the locator "c." (chapter), hence the look-behind
CITATION = re.compile(r"\d|(?<!&)\b(?:lib|cap|sect|tom|epist|consil|fol|memb|subs|c|l)\.|^\s*(?:idem|ibid|ib)\b"
                      r"|^\s*[ivxlcdm]{1,6}\.?\s*$", re.I)
# A work cited by author and title: "Grotius de verit.", "Levinus Lemnius de occult." — one to three
# capitalised words, "de", and a title word cut off by an abbreviation stop.
WORK_TITLE = re.compile(r"^\s*(?:\p{Lu}[\p{L}’']*\.?\s+){1,3}de\s+\p{L}+\.")
TITLE_WORDS = {"de", "in", "&", "et"}
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
    return not isinstance(x, str) and x.tag == T("hi") and x.get("rend") == "i"


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
    titles = [bool(WORK_TITLE.match(p)) for p in pieces]
    caps = [_capitalised(p) for p, t in zip(pieces, titles, strict=True) if not t]
    # every piece a reference or capitalised, and most capitalised pieces names rather than Latin terms
    if not all(caps) or sum(_latin_term(c) for c in caps) * 2 > len(caps):
        return None
    lower = [w.lower() for w in WORD.findall(ETC.sub(" ", text))]
    if any((w in LA_FUNCTION and w not in TITLE_WORDS) or w in EN_FUNCTION for w in lower):
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
    items = take_items(e)
    out, last = [], 0
    queue = _runs(items)
    while queue:
        i, j = queue.pop(0)
        text = text_of(items[i:j])
        bracket = _bracketed(items, i, j)
        verdict, conf, why = classify(text, bracket, in_note, _stop_after(items, j) and not bracket)
        if not bracket and _dotted_citation(items, i, j):
            verdict, conf, why = ("citation", "medium",
                                  "short fragments separated by full stops (e.g. 'Donat. vita. ejus')")
        elif not bracket and re.fullmatch(r"\s*\p{Lu}?\p{Ll}+-\p{Ll}+\s*", text):
            verdict, conf, why = "en", "medium", "hyphenated compound (an English loan-word, e.g. 'Bona-roba')"
        elif verdict != "la" and (pieces := _resplit(items, i, j, verdict, in_note)):
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
        if verdict in ("undetermined", "name"):
            # the rules cannot decide: use the model's ruling if there is one (machine layer, labelled)
            adj = adjudicated(unit, text)
            if adj and adj["confidence"] == "low":
                adj = None  # the model was unsure: leave the rules' verdict and keep it for review
            if re.fullmatch(r"\s*&c\.?\s*", text):
                adj = None  # "&c" alone is "etc.": not a passage to translate
                verdict, why = "en", "&c alone (etc.)"
            if adj and adj["label"] in MODEL_LANGS:
                verdict, lang, resp = "la", adj["label"], "#model"
                if lang == "grc" and not re.search(r"\p{Script=Greek}", text):
                    lang = "grc-Latn"  # Greek written in Latin letters (e.g. Aristophanes' frogs)
                if lang == "he" and not re.search(r"\p{Script=Hebrew}", text):
                    lang = "he-Latn"  # Hebrew written in Latin letters
                conf = "medium" if adj["confidence"] == "high" else adj["confidence"]
                why = f"model ruling ({adj['model']}/{adj['prompt']}): {adj['label']} {adj['kind']}"
            elif adj:
                verdict, why = adj["label"], f"model ruling ({adj['model']}/{adj['prompt']}): {adj['label']}"
        if verdict == "la" and j - i > 1 and resp == "#rules":
            i, j = _trim_run(items, i, j, in_note, bracket)
            text = text_of(items[i:j])
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
        while j - a > 1 and _citation_like(items, a, in_note):
            a += 2
        rest = text_of(items[a:j])
        if a > i and len(WORD.findall(rest)) >= 3 and classify(rest, True, in_note)[0] == "la":
            return [(i, a - 1), (a, j)]
    if verdict != "en":
        return None
    cuts = [k for k in range(i, j - 2, 2) if _sentence_break(items, k)]
    if not cuts:
        return None
    bounds = list(zip([i, *[k + 2 for k in cuts]], [*[k + 1 for k in cuts], j], strict=True))
    if any(len(WORD.findall(text_of(items[s:e]))) >= 2 and
           classify(text_of(items[s:e]), e == j and bracket, in_note, _stop_after(items, e))[0] == "la"
           for s, e in bounds):
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
    while b - a > 1 and _citation_like(items, a, in_note):
        a += 2
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
    finalize_lang(div)
    correct_languages(div, unit, stats)
    for d in decisions:
        stats[f"italic-run:{d['verdict']}"] += 1
    return decisions


def is_foreign(x) -> bool:
    return not isinstance(x, str) and (local(x.tag) == "foreign" or x.get("ana") == "foreign")
