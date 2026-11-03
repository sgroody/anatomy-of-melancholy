"""`burton xrefs`: Burton's explicit internal cross-references -> data/layers/xrefs/<unit>.json.

Only references naming Burton's own divisions are taken: Part./Partit., Memb., Subs./Subsect. (with or
without Sect.). A bare "Sect. 3" is skipped and counted as ambiguous, because "sect." also appears in
Burton's citations of other authors' books. Missing levels are inherited from the subsection the
reference stands in ("Memb. 3" in 1.2.2.5 means 1.2.3). Nothing is guessed: a target that does not exist
is recorded as unresolved and rendered unlinked. Relative references ("as I have said") are not handled here.

Records use text-quote selectors into the unit's public text; the base text is never changed.
"""

import json
import re
from collections import Counter

from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..ingest.epub import FRONT, all_units, nav
from ..tei import T
from ..textview import public_text

LABEL = r"(Part(?:it)?|Sect|Memb?|Subs(?:ect)?|Sub)\.?"
PAIR = re.compile(rf"\b{LABEL}\s*(\d+)", re.I)
LEVEL = {"part": 0, "partit": 0, "sect": 1, "memb": 2, "mem": 2, "subs": 3, "subsect": 3, "sub": 3}


CUE = re.compile(r"\b(see|vide|before|above|below|hereafter|following|follow|precedent|preceding|"
                 r"former|formerly|last|next|in his place|as i have|i have (?:shown|showed|said|treated)|"
                 r"shall (?:show|treat|speak)|(?:in )?(?:the|this|that|my) (?:partition|section|member|subsection)|"
                 r"handled|discoursed|elsewhere|in the synopsis|sequel)\b[^.;¶]*$")
# a book-title abbreviation ("Anat. ingen.") or a locator ("lib. 3") just before: another author's work
EXTERNAL_BEFORE = re.compile(r"(?:\b[A-Za-z]{2,}\.\s*$)"
                             r"|(?:\b(?:lib|cap|tract|fol|tom|epist|com|c|l)\.?\s*\d+[,.]?\s*$)")
EXTERNAL_AFTER = re.compile(r"^\W*(?:cap|lib|fol|ver|vers|tract|v|c|quaest|q|art|dist|disp|lect)\b", re.I)
SKIPPED: list = []  # (unit, before, match, after) of matches not taken, for review


def _groups(text: str) -> list[tuple[int, int, list[tuple[int, int]]]]:
    """Runs of (level, number) pairs close together: [(start, end, [(level, n), ...])].
    Pairs are grouped only within one note or paragraph (never across the ¶ separator)."""
    out = []
    for m in PAIR.finditer(text):
        lvl, n = LEVEL[m.group(1).lower()], int(m.group(2))
        gap = text[out[-1][1]:m.start()] if out else ""
        if out and len(gap) <= 4 and "¶" not in gap and lvl not in [p[0] for p in out[-1][2]]:
            out[-1] = (out[-1][0], m.end(), out[-1][2] + [(lvl, n)])
        else:
            out.append((m.start(), m.end(), [(lvl, n)]))
    return out


def resolve(here: str, pairs: list[tuple[int, int]], keys: set[str]) -> tuple[str | None, str]:
    """Target unit id (or a division prefix like '1.2.3') and status."""
    if here in FRONT or not here[:1].isdigit():  # front and back matter have no division of their own
        cur = [None, None, None, None]
    else:
        cur = [int(x) for x in here.split(".")]
    given = dict(pairs)
    top = min(given)
    if any(lv not in given for lv in range(top, max(given) + 1)):
        return None, "unresolved"  # a level is skipped ("Part. 1 Subs. 2 Memb. 2"): resolving it would be a guess
    target = []
    for lvl in range(4):
        if lvl in given:
            target.append(given[lvl])
        elif lvl < top:
            if cur[lvl] is None:
                return None, "unresolved"  # e.g. "Memb. 3" in the front matter: no context to inherit
            target.append(cur[lvl])
        else:
            break
    if len(target) == 4:
        tid = ".".join(map(str, target))
        return (tid, "explicit-resolved") if tid in keys else (tid, "unresolved")
    prefix = ".".join(map(str, target)) + "."
    first = next((k for k in sorted(keys, key=lambda k: [int(x) for x in k.split(".")]) if k.startswith(prefix)), None)
    return (first, "explicit-resolved") if first else (prefix.rstrip("."), "unresolved")


def build(units: list[str] | None = None) -> Counter:
    units = units or all_units()
    keys = {u["unit"] for u in nav()}
    stats: Counter = Counter()
    for unit in units:
        root = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot()
        if root.find(f".//{T('div')}").get("resp") == "#gowland":
            continue
        div = root.find(f".//{T('div')}")
        # running text and notes only: headings ("SUBSECT. 3.") are labels, not references
        blocks = div.iter(T("p"), T("l"), T("item"), T("note"))
        text = " ¶ ".join(public_text(b, notes=b.tag == T("note")) for b in blocks
                         if not any(a.tag == T("note") for a in b.iterancestors()))
        records = {}
        for s, e, pairs in _groups(text):
            levels = {p[0] for p in pairs}
            before, after = text[max(0, s - 60):s], text[e:e + 12]
            cue = CUE.search(before.lower())
            external = EXTERNAL_BEFORE.search(text[max(0, s - 22):s]) or EXTERNAL_AFTER.match(after)
            burtonish = bool(levels & {2, 3})
            if levels == {1} and not cue:
                stats["skipped-bare-sect"] += 1
                continue
            if EXTERNAL_AFTER.match(after) or (not cue and (external or not burtonish or len(levels) < 2)):
                stats["skipped-external-or-ambiguous"] += 1
                SKIPPED.append((unit, before[-40:], text[s:e], after))
                continue
            exact = text[s:e]
            target, status = resolve(unit, pairs, keys)
            stats[status] += 1
            n = len(records) + 1
            records[f"{unit}-x{n}"] = {
                "selector": {"in": unit, "exact": exact, "prefix": text[max(0, s - 30):s], "suffix": text[e:e + 30]},
                "target": target, "status": status, "method": "rules/xref-v1",
                "levels": {["part", "sect", "memb", "subsect"][lv]: v for lv, v in pairs},
            }
        out = paths.LAYERS / "xrefs" / f"{unit}.json"
        if records:
            out.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(out, json.dumps(records, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        elif out.exists():
            out.unlink()
        stats["units-with-xrefs"] += bool(records)
    return stats
