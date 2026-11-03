"""`burton verify` / `burton check`: the V-checks of SPEC §9, reported as counts.

Text-side checks read data/text/*.xml with plain lxml and compare against burton.verify.epub_counts.
Nothing here imports burton.ingest (independence rule, CLAUDE.md).
"""

import difflib
import json
import re
import unicodedata
from datetime import UTC, datetime

import yaml
from lxml import etree

from .. import paths
from . import epub_counts

TEI = "{http://www.tei-c.org/ns/1.0}"
ED = "{https://burton-edition.local/ns/gowland}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
HEBREW = re.compile(r"[֐-׿יִ-ﭏ]")
ARABIC = re.compile(r"[؀-ۿ]")
TEI_BLOCK = {f"{TEI}{t}" for t in ("head", "p", "l", "lg", "quote", "div", "list", "item", "lb")}


class Result:
    def __init__(self, code: str, name: str):
        self.code, self.name = code, name
        self.ok = True
        self.counts: dict = {}
        self.problems: list[str] = []
        self.deferred: str | None = None  # set by report() from data/manual/deferred-checks.yaml

    def fail(self, msg: str) -> None:
        self.ok = False
        self.problems.append(msg)

    def line(self) -> str:
        c = ", ".join(f"{k}={v}" for k, v in self.counts.items())
        status = "PASS" if self.ok else "DEFER" if self.deferred else "FAIL"
        return f"{status}  {self.code} {self.name}: {c}"


def norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).split())


def load_tei(unit: str):
    return etree.parse(str(paths.TEXT / f"{unit}.xml"))


def is_editor_text(e) -> bool:
    """Text WE added, absent from the EPUB: transcribed heading images, corrections, supplied words.
    (resp="#editor" on other elements records an editorial *markup* decision, not added text.)"""
    return ((e.tag == f"{TEI}head" and e.get("facs") is not None) or e.tag == f"{TEI}corr"
            or (e.tag == f"{TEI}supplied" and e.get("resp") == "#editor"))


def tei_text(root, *, notes: bool) -> tuple[str, list[str]]:
    """Plain text of the base text as the EPUB shows it: editor additions out, sic not corr,
    note-marker numbers absent. Returns (main text, [note texts in order])."""
    main: list[str] = []
    note_texts: list[str] = []

    def walk(e, out):
        if not isinstance(e.tag, str):
            return
        if is_editor_text(e):
            return
        if e.tag == f"{TEI}note":
            buf: list[str] = []
            if e.text:
                buf.append(e.text)
            for c in e:
                walk(c, buf)
                if c.tail:
                    buf.append(c.tail)
            note_texts.append("".join(buf))
            return
        block = e.tag in TEI_BLOCK
        if block:
            out.append("\n")
        if e.text:
            out.append(e.text)
        for c in e:
            walk(c, out)
            if c.tail:
                out.append(c.tail)
        if block:
            out.append("\n")

    walk(root.find(f".//{TEI}div"), main)
    return "".join(main), note_texts


def word_diff(a: str, b: str, limit: int = 6) -> list[str]:
    aw, bw = a.split(), b.split()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=aw, b=bw, autojunk=False).get_opcodes():
        if tag != "equal":
            out.append(f"{tag}: EPUB {' '.join(aw[i1:i2])[:80]!r} vs XML {' '.join(bw[j1:j2])[:80]!r}")
            if len(out) >= limit:
                break
    return out


def load_allowed() -> list[dict]:
    f = paths.VERIFY / "allowed-diffs.yaml"
    if not f.exists():
        return []
    import yaml

    return yaml.safe_load(f.read_text(encoding="utf-8")) or []


# ------------------------------------------------------------------ text checks

def v1_roundtrip(unit: str, ec: dict, root) -> Result:
    r = Result("V1", "text round-trip vs EPUB")
    main, notes = tei_text(root, notes=True)
    a, b = norm(ec["main_text"]), norm(main)
    r.counts["main_words"] = len(a.split())
    diffs = word_diff(a, b) if a != b else []
    allowed = [d for d in load_allowed() if d.get("unit") == unit]
    unexplained = [d for d in diffs if not any(x["match"] in d for x in allowed)]
    r.counts["main_unexplained_diffs"] = len(unexplained)
    for d in unexplained:
        r.fail(f"{unit} main: {d}")
    bad_notes = 0
    for i, (e, t) in enumerate(zip(ec["sidenote_texts"], notes, strict=False), 1):
        if e is None or norm(e) != norm(t):
            bad_notes += 1
            r.fail(f"{unit} note {i}: EPUB {norm(e or '')[:60]!r} vs XML {norm(t)[:60]!r}")
    if len(ec["sidenote_texts"]) != len(notes):
        r.fail(f"{unit}: {len(ec['sidenote_texts'])} EPUB notes vs {len(notes)} XML notes")
    r.counts["notes_compared"] = len(notes)
    r.counts["note_mismatches"] = bad_notes
    r.counts["editor_additions_excluded"] = sum(1 for e in root.iter() if isinstance(e.tag, str) and is_editor_text(e))
    return r


def v2_counts(unit: str, ec: dict, root) -> Result:
    r = Result("V2", "per-unit counts EPUB = XML")
    div = root.find(f".//{TEI}div")
    xml = {
        "sidenote_refs": len(div.findall(f".//{TEI}note")),
        "endnote_refs": len(div.findall(f".//{ED}enref")),
        "pagebreaks": len(div.findall(f".//{TEI}pb")),
        "paragraphs": sum(1 for p in div.iter(f"{TEI}p") if p.getparent().tag != f"{TEI}note"),
        "verse_lines": len(div.findall(f".//{TEI}l")),
        "greek_chars": len(GREEK.findall(tei_text(root, notes=True)[0])),
        "heading_images": len(div.xpath(".//*[@facs]")),
    }
    for k, v in xml.items():
        r.counts[k] = f"{ec[k]}/{v}"
        if ec[k] != v:
            r.fail(f"{unit} {k}: EPUB {ec[k]} vs XML {v}")
    return r


def v3_notes(unit: str, ec: dict, root) -> Result:
    r = Result("V3", "note integrity")
    notes = root.findall(f".//{TEI}note")
    src_n = [int(n.get("srcN")) for n in notes]
    shown = [int(n.get("n")) for n in notes]
    r.counts["sidenotes_resolved"] = f"{sum(1 for t in ec['sidenote_texts'] if t is not None)}/{len(notes)}"
    if src_n != ec["sidenote_numbers"]:
        r.fail(f"{unit}: note numbers {src_n} vs EPUB {ec['sidenote_numbers']}")
    if shown != list(range(1, len(notes) + 1)):
        r.fail(f"{unit}: display numbers not 1..{len(notes)}")
    if any(t is None for t in ec["sidenote_texts"]):
        r.fail(f"{unit}: a sidenote reference has no body in the EPUB")
    ids = [e.get(XML_ID) for e in root.iter() if isinstance(e.tag, str) and e.get(XML_ID)]
    r.counts["ids"] = len(ids)
    if len(ids) != len(set(ids)):
        r.fail(f"{unit}: duplicate xml:id")
    empty = [n.get(XML_ID) for n in notes if not norm("".join(n.itertext()))]
    if empty:
        r.fail(f"{unit}: empty notes {empty}")
    return r


def script_violations(root, lang_attr: str) -> tuple[int, list[str]]:
    """Greek/Hebrew/Arabic characters with no ancestor carrying the matching language."""
    bad: list[str] = []
    total = 0
    want = [(GREEK, ("grc", "el")), (HEBREW, ("he", "hbo")), (ARABIC, ("ar",))]

    def lang_of(e):
        while e is not None:
            v = e.get(lang_attr)
            if v:
                return v
            e = e.getparent()
        return None

    for e in root.iter():
        if not isinstance(e.tag, str):
            continue
        for text, owner in ((e.text, e), (e.tail, e.getparent())):
            if not text or owner is None:
                continue
            for rx, langs in want:
                for m in rx.finditer(text):
                    total += 1
                    if lang_of(owner) not in langs:
                        bad.append(f"{m.group(0)!r} in {text.strip()[:40]!r}")
    return total, bad


def v4_scripts(unit: str, root) -> Result:
    r = Result("V4", "foreign scripts language-tagged")
    total, bad = script_violations(root, XML_LANG)
    r.counts["script_chars"] = total
    r.counts["untagged"] = len(bad)
    for b in bad[:10]:
        r.fail(f"{unit}: untagged {b}")
    return r


def v5_langid(units: list[str]) -> Result:
    """Language identification vs the hand-checked gold sample (SPEC §6.1), each item judged in place.
    Thresholds: precision >= 0.98, recall >= 0.97, boundary exact-match >= 0.95."""
    from . import gold

    r = Result("V5", f"language-ID vs gold samples (gate: held-out {gold.GATE})")
    tune = gold.evaluate(units)
    held = gold.evaluate(units, holdout=True)
    seen = [gold.evaluate(units, holdout=h["name"]) for h in gold.HOLDOUTS[:-1]]
    r.counts.update({f"heldout_{gold.GATE}": gold.summary(held),
                     **{f"seen_{s['sample']}": gold.summary(s) for s in seen},
                     "tuning": gold.summary(tune)})
    r.problems = ([f"held-out {gold.GATE}: " + m for m in held["misses"]]
                  + [f"seen {s['sample']}: " + m for s in seen for m in s["misses"]]
                  + ["tuning: " + m for m in tune["misses"]])
    # Only the newest hold-out round was never seen while the rules changed, so only it can show that
    # they meet the targets. The tuning sample and earlier rounds are reported, never gated on.
    if units is None or len(units) > 100:  # whole-book run: the gate round must exist and be labelled
        if not held["labelled"]:
            r.ok = False
            r.problems.insert(0, f"held-out round {gold.GATE} is not labelled ({gold.HOLDOUT_GOLD.name} missing)")
            return r
    if held["tp"] + held["fn"] >= 40:
        r.ok = ((held["precision"] or 0) >= 0.98 and (held["recall"] or 0) >= 0.97
                and (held["boundary_exact"] or 0) >= 0.95)
        if not r.ok:
            r.problems.insert(0, f"held-out {gold.GATE} below target: precision >= 0.98, recall >= 0.97, "
                                 "boundary >= 0.95")
    return r


def _text_without_notes(e):
    if e.text:
        yield e.text
    for c in e:
        if c.tag != f"{TEI}note":
            yield from _text_without_notes(c)
        if c.tail:
            yield c.tail


# ------------------------------------------------------------------ drivers

def v1_files(units: list[str]) -> Result:
    """Coverage: each EPUB page's whole text = its units' texts concatenated. Catches anything that
    falls between unit boundaries (the per-unit V1 cannot, since it uses boundaries itself)."""
    r = Result("V1f", "every EPUB page fully covered by its units")
    by_file = epub_counts.units_by_file(paths.XHTML)
    checked = 0
    for fname, fu in by_file.items():
        if not set(fu) <= set(units):
            continue
        epub_text = norm(epub_counts.file_text(paths.XHTML, fname))
        xml_text = norm(" ".join(tei_text(load_tei(u), notes=True)[0] for u in fu))
        checked += 1
        if epub_text != xml_text:
            for d in word_diff(epub_text, xml_text, limit=3):
                r.fail(f"{fname}: {d}")
    r.counts = {"pages_checked": checked, "pages_total": len(by_file)}
    return r


def v3_endnotes(units: list[str]) -> Result:
    """Gowland's endnotes (private build): texts equal the EPUB's; every anchor resolves; on a whole-book
    run every endnote is referenced exactly once. Link corrections must be recorded (@sic)."""
    r = Result("V3g", "Gowland endnotes: text and links")
    f = paths.TEXT / "gowland-endnotes.xml"
    if not f.exists():
        r.fail("data/text/gowland-endnotes.xml missing: run `burton ingest --all`")
        return r
    root = etree.parse(str(f)).getroot()
    xml = {e.get(XML_ID): norm("".join(e.itertext())) for e in root.iter(f"{ED}endnote")}
    epub = {}
    for name in epub_counts.ENDNOTE_FILES:
        for a in epub_counts.doc(paths.XHTML, name).getroot().iter("{http://www.w3.org/1999/xhtml}aside"):
            epub[a.get("id")] = norm(epub_counts.plain(a))
    mismatched = [k for k in epub if xml.get(k) != epub[k]]
    for k in mismatched[:8]:
        r.fail(f"endnote {k}: EPUB {epub[k][:50]!r} vs XML {xml.get(k, '')[:50]!r}")
    refs: dict[str, int] = {}
    fixed = 0
    for unit in units:
        for e in load_tei(unit).iter(f"{ED}enref"):
            refs[e.get("target")] = refs.get(e.get("target"), 0) + 1
            fixed += e.get("sic") is not None
            if e.get("target") not in xml:
                r.fail(f"{unit}: endnote anchor {e.get('target')} has no body")
    full_book = len(units) >= len(epub_counts.units_by_file(paths.XHTML)) and len(units) > 150
    if full_book:
        orphans = [k for k in xml if k not in refs]
        doubles = [k for k, n in refs.items() if n > 1]
        for k in orphans[:8]:
            r.fail(f"endnote {k} is referenced by no anchor")
        for k in doubles[:8]:
            r.fail(f"endnote {k} is referenced {refs[k]} times")
        r.counts.update({"orphans": len(orphans), "referenced_twice": len(doubles)})
    r.counts = {"bodies": f"{len(epub)}/{len(xml)}", "text_mismatches": len(mismatched),
                "anchors": sum(refs.values()), "link_fixes_applied": fixed, **r.counts}
    return r


BRACKET = re.compile(r"[\[\]{}]")


def v8_public_text(units: list[str]) -> Result:
    """V8t: the public text view (what models and the public build get) has no Gowland bracket left.

    Every [translation] and {interpolation} must be separated as ed:* / supplied[@resp=#gowland];
    a bracket still in public_text means ingest missed one (CLAUDE.md rule 5). Units that are wholly
    Gowland's (div[@resp=#gowland]) are never public and are only counted."""
    from ..textview import public_text

    r = Result("V8t", "public text has no Gowland brackets")
    n = {"trans": 0, "trans_pieces": 0, "verse_trans": 0, "supplied": 0, "brackets_left": 0, "gowland_units": 0}
    for unit in units:
        div = load_tei(unit).getroot().find(f".//{TEI}div")
        if div.get("resp") == "#gowland":
            n["gowland_units"] += 1
            continue
        for t in div.iter(f"{ED}trans", f"{ED}verse-trans"):
            key = "trans" if t.tag == f"{ED}trans" else "verse_trans"
            n[key] += t.get("part") in (None, "I")  # a translation running over blocks counts once
            n["trans_pieces"] += t.tag == f"{ED}trans" and t.get("part") is not None
        n["supplied"] += sum(1 for s in div.iter(f"{TEI}supplied") if s.get("resp") == "#gowland")
        text = public_text(div, notes=True)
        for m in BRACKET.finditer(text):
            n["brackets_left"] += 1
            r.fail(f"{unit}: unseparated {m.group()!r} in public text: "
                   f"{text[max(0, m.start() - 50):m.start() + 30]!r}")
    r.counts = {**n, "units": len(units)}
    return r


def _add(a, b):
    """Sum counts across units; "x/y" fractions are summed part by part."""
    if a is None:
        return b
    if isinstance(b, str) and "/" in b:
        (a1, a2), (b1, b2) = (map(int, a.split("/")), map(int, b.split("/")))
        return f"{a1 + b1}/{a2 + b2}"
    return a + b if isinstance(b, int) else b


def text_results(units: list[str]) -> list[Result]:
    results = []
    per = {code: Result(code, name) for code, name in (
        ("V1", "text round-trip vs EPUB"), ("V2", "per-unit counts EPUB = XML"),
        ("V3", "note integrity"), ("V4", "foreign scripts language-tagged"))}
    for unit in units:
        ec = epub_counts.unit_counts(paths.XHTML, unit)
        root = load_tei(unit)
        for res in (v1_roundtrip(unit, ec, root), v2_counts(unit, ec, root), v3_notes(unit, ec, root),
                    v4_scripts(unit, root)):
            agg = per[res.code]
            agg.ok &= res.ok
            agg.problems += res.problems
            for k, v in res.counts.items():
                agg.counts[k] = _add(agg.counts.get(k), v)
    for agg in per.values():
        agg.counts["units"] = len(units)
    results += per.values()
    results.append(v1_files(units))
    results.append(v3_endnotes(units))
    results.append(v8_public_text(units))
    results.append(v5_langid(units))
    from . import layers

    results.append(layers.v7_layers(units))
    from . import synopses

    results.append(synopses.v11_synopses())
    return results


def deferred_checks() -> dict:
    """Owner decisions that a failing check does not fail the build (data/manual/deferred-checks.yaml)."""
    f = paths.MANUAL / "deferred-checks.yaml"
    return (yaml.safe_load(f.read_text(encoding="utf-8")) or {}) if f.exists() else {}


def report(results: list[Result], name: str = "latest") -> bool:
    deferred = deferred_checks()
    for r in results:
        if not r.ok and r.code in deferred:
            d = deferred[r.code]
            r.deferred = f"deferred by {d['decision']} ({d['date']}): {' '.join(d['reason'].split())}"
    ok = all(r.ok or r.deferred for r in results)
    for r in results:
        print(r.line())
        if r.deferred:
            print(f"      ! {r.deferred}")
        for p in r.problems[:12]:
            print(f"      - {p}")
    paths.REPORTS.mkdir(parents=True, exist_ok=True)
    data = {"when": datetime.now(UTC).isoformat(timespec="seconds"), "ok": ok,
            "results": [{"code": r.code, "name": r.name, "ok": r.ok, "deferred": r.deferred, "counts": r.counts,
                         "problems": r.problems} for r in results]}
    (paths.REPORTS / f"{name}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK" if ok else "FAILED", f"-> verify/reports/{name}.json")
    return ok


def verify_text(units: list[str]) -> int:
    return 0 if report(text_results(units), "text") else 1
