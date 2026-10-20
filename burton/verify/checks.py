"""`burton verify` / `burton check`: the V-checks of SPEC §9, reported as counts.

Text-side checks read data/text/*.xml with plain lxml and compare against burton.verify.epub_counts.
Nothing here imports burton.ingest (independence rule, CLAUDE.md).
"""

import difflib
import json
import re
import unicodedata
from datetime import UTC, datetime

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
TEI_BLOCK = {f"{TEI}{t}" for t in ("head", "p", "l", "lg", "quote", "div")}


class Result:
    def __init__(self, code: str, name: str):
        self.code, self.name = code, name
        self.ok = True
        self.counts: dict = {}
        self.problems: list[str] = []

    def fail(self, msg: str) -> None:
        self.ok = False
        self.problems.append(msg)

    def line(self) -> str:
        c = ", ".join(f"{k}={v}" for k, v in self.counts.items())
        return f"{'PASS' if self.ok else 'FAIL'}  {self.code} {self.name}: {c}"


def norm(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).split())


def load_tei(unit: str):
    return etree.parse(str(paths.TEXT / f"{unit}.xml"))


def tei_text(root, *, notes: bool) -> tuple[str, list[str]]:
    """Plain text of the base text as the EPUB shows it: editor additions out, sic not corr,
    note-marker numbers absent. Returns (main text, [note texts in order])."""
    main: list[str] = []
    note_texts: list[str] = []

    def walk(e, out):
        if not isinstance(e.tag, str):
            return
        if e.get("resp") == "#editor" or e.tag == f"{TEI}corr":
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
    r.counts["editor_additions_excluded"] = len(root.xpath("//*[@resp='#editor']"))
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
    """Rules vs the hand-checked gold sample, for the units that have gold labels."""
    r = Result("V5", "language-ID vs gold sample")
    gold_file = paths.DATA / "eval" / "langid-gold.jsonl"
    rows = [json.loads(x) for x in gold_file.read_text(encoding="utf-8").splitlines()[1:]]
    tp = fp = fn = 0
    misses = []
    for unit in units:
        root = load_tei(unit)
        tagged = []
        for e in root.iter():
            if isinstance(e.tag, str) and e.get("ana") == "foreign":
                tagged.append(norm("".join(t for t in _text_without_notes(e))))
        for g in (x for x in rows if x["unit"] == unit):
            is_foreign = g["gold"] in ("la", "grc", "it", "fr", "es", "de", "nl", "enm", "he")
            key = norm(g["text"])
            hit = any(key == t or (g.get("match") == "lg" and t.startswith(key.split(" … ")[0]))
                      or (key.startswith("———") and t == norm(key.replace("———", "", 1)))
                      or t.replace("——— ", "") == key.replace("——— ", "") for t in tagged)
            if is_foreign and hit:
                tp += 1
            elif is_foreign:
                fn += 1
                misses.append(f"missed {g['gold']} {g['kind']}: {g['text'][:50]!r}")
            elif hit:
                fp += 1
                misses.append(f"false foreign: {g['text'][:50]!r}")
    p = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    r.counts.update({"gold_items": sum(1 for x in rows if x["unit"] in units), "tp": tp, "fp": fp, "fn": fn,
                     "precision": f"{p:.3f}", "recall": f"{rec:.3f}"})
    r.problems = misses
    # M1 reports V5; the pass thresholds (P>=0.98, R>=0.97) gate M2, after model adjudication.
    r.ok = True
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
                agg.counts[k] = v if len(units) == 1 else agg.counts.get(k, 0) + (v if isinstance(v, int) else 0)
    results += per.values()
    results.append(v5_langid(units))
    from . import layers

    results.append(layers.v7_layers(units))
    return results


def report(results: list[Result], name: str = "latest") -> bool:
    ok = all(r.ok for r in results)
    for r in results:
        print(r.line())
        for p in r.problems[:12]:
            print(f"      - {p}")
    paths.REPORTS.mkdir(parents=True, exist_ok=True)
    data = {"when": datetime.now(UTC).isoformat(timespec="seconds"), "ok": ok,
            "results": [{"code": r.code, "name": r.name, "ok": r.ok, "counts": r.counts,
                         "problems": r.problems} for r in results]}
    (paths.REPORTS / f"{name}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK" if ok else "FAILED", f"-> verify/reports/{name}.json")
    return ok


def verify_text(units: list[str]) -> int:
    return 0 if report(text_results(units), "text") else 1
