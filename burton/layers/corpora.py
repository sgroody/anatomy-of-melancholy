"""`burton corpora`: convert downloaded corpora to the verifier's plain format (data/source/corpora/).

Perseus canonical-latinLit (TEI, CTS): every Latin edition file becomes
data/source/corpora/perseus-latin/<author-id>/<textgroup>.<work>.txt, one `locus<TAB>text` line per innermost
citable unit (div[@type=textpart], loci joined from the ancestors' @n, e.g. "1.4" for a poem in book 1). Text
excludes notes, headings and bibliographic matter. Author ids come from data/corpora/perseus-latin.yaml. The
downloaded files are untrusted data: parsed with entities and network access off, never executed.
"""

import json
import shutil
from collections import Counter

import yaml
from lxml import etree

from .. import paths

RAW = paths.SOURCE / "corpora-raw" / "perseus-latin" / "data"
OUT = paths.SOURCE / "corpora" / "perseus-latin"
MAP = paths.DATA / "corpora" / "perseus-latin.yaml"
TEI = "{http://www.tei-c.org/ns/1.0}"
SKIP = {f"{TEI}{t}" for t in ("note", "head", "bibl", "ref", "del", "gap", "milestone", "lb", "pb")}


def _text(e) -> str:
    out = []

    def walk(x):
        if x.tag in SKIP:
            pass
        else:
            if x.text:
                out.append(x.text)
            for c in x:
                walk(c)
        if x is not e and x.tail:
            out.append(x.tail)

    walk(e)
    return " ".join("".join(out).split())


def units(path) -> list[tuple[str, str]]:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True, load_dtd=False,
                             recover=True)  # a few files use HTML entities (&mdash;) without a DTD: dropped
    root = etree.parse(str(path), parser).getroot()
    units.recovered += bool(parser.error_log)
    parts = root.iter(f"{TEI}div")
    leaves = [d for d in parts if d.get("type") == "textpart"
              and not any(c.get("type") == "textpart" for c in d.iter(f"{TEI}div") if c is not d)]
    out = []
    for d in leaves:
        loc = [a.get("n") for a in reversed(list(d.iterancestors(f"{TEI}div"))) if a.get("type") == "textpart"]
        out.append((".".join([*filter(None, loc), d.get("n") or "?"]), _text(d)))
    if not out:  # no textparts: the edition as one unit
        body = root.find(f".//{TEI}body")
        if body is not None:
            out.append(("all", _text(body)))
    return [(loc, t) for loc, t in out if t]


units.recovered = 0


def convert() -> Counter:
    authors = yaml.safe_load(MAP.read_text(encoding="utf-8"))["authors"]
    if OUT.exists():  # a re-run must not leave files under an author's old (unmapped) name
        shutil.rmtree(OUT)
    stats: Counter = Counter()
    index = {}
    for f in sorted(RAW.glob("*/*/*lat*.xml")):
        group, work = f.parent.parent.name, f.parent.name
        author = authors.get(group, f"perseus-{group}")
        rows = units(f)
        dest = OUT / author / f"{group}.{work}.{f.stem.rsplit('.', 1)[-1]}.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("".join(f"{loc}\t{t}\n" for loc, t in rows), encoding="utf-8", newline="\n")
        cts = f.parent / "__cts__.xml"
        title = None
        if cts.exists():
            t = etree.parse(str(cts), etree.XMLParser(resolve_entities=False, no_network=True, recover=True))
            title = next((x.text for x in t.iter("{http://chs.harvard.edu/xmlns/cts}title") if x.text), None)
        index[dest.relative_to(OUT).as_posix()] = {"source": f.relative_to(RAW).as_posix(), "units": len(rows),
                                                   "title": title}
        stats["files"] += 1
        stats["units"] += len(rows)
        stats["mapped" if group in authors else "unmapped"] += 1
    stats["files_recovered"] = units.recovered
    (OUT / "index.json").write_text(json.dumps(index, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return stats
