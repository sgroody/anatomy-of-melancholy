"""Prototype: Burton's synopses re-set by the printer's own rules, responsive by container queries (2026-11-19).

Writes state/review/synopsis-sheets-2026-11-19.html (serve the repository root with the `review-pages` launch entry,
port 8790; it borrows fonts and images from site/private, so build first). Words come from data/synopses/pN.json
verbatim, through burton.site.synopsis.runs_html; nothing here writes data.

    uv run python tools/synopsis_sheets/proto.py
"""

import json
import re
from pathlib import Path

from burton.site.render import attr, esc
from burton.site.synopsis import load, runs_html

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "state" / "review" / "synopsis-sheets-2026-11-19.html"
HERE = Path(__file__).resolve().parent
SITE = "../../site/private/"  # from state/review/
PARTS = {"p1": "The First Partition", "p2": "The Second Partition", "p3": "The Third Partition"}

# Burton's locator, as rendered: "<i>Subsect</i>. <i>2</i>", "<i>Sect 1 Memb. 1</i>",
# "<i>Memb</i>. <i>4 Sect</i>. <i>2</i>", "<i>1st Memb</i>.", "<i>4th</i>. <i>Subsect</i>.", "<i>Memb. 2.</i>"
DIV = r"(?:Sect|Memb|Subsect|Subs)\b"
ORD = r"(?:<i>)?(?:\d+(?:st|nd|rd|th)\b(?:</i>)?\.?\s*(?:<i>)?)?"  # "2nd", "4th</i>. <i>"
LOC = re.compile(ORD + DIV + r"(?:[.\s,\d]|</?i>|" + DIV + r")*")
# a numbered member with no division word, read by its column ("1.", "2nd.", "<i>3</i>.")
LEAD = re.compile(r"^(?:<i>)?\d+(?:st|nd|rd|th)?(?:</i>)?")


def _trim(s: str) -> str | None:
    """A match cut back to whole tags and words: no lone tag at either end, no trailing space, comma or full stop."""
    prev = None
    while s != prev:
        prev = s
        s = re.sub(r"(?:<i>|[\s,])+$", "", s)
        s = re.sub(r"^</i>", "", s)
        if s.endswith("</i>."):
            s = s[:-1]
        if s.count("<i>") > s.count("</i>") and s.startswith("<i>"):
            s = s[3:]
        if s.count("</i>") > s.count("<i>") and s.endswith("</i>"):
            s = s[:-4]
    return s if re.search(r"\d", s) and s.count("<i>") == s.count("</i>") else None


def height(n: dict) -> int:
    """Levels below a node (a leaf is 0)."""
    return 1 + max(map(height, n["children"])) if n["children"] else 0


def count(n: dict) -> int:
    return sum(1 + count(c) for c in n["children"])


def units_of(refs: list[dict]) -> list[str]:
    units = []
    for r in refs:
        if r["unit"] and r["unit"] not in units:
            units.append(r["unit"])
    return units


def link_locators(text: str, units: list[str], lead: bool = False) -> tuple[str, int]:
    """Burton's own italic locator words become the link (no chip added). Several units in one locator ("9, 10, 11")
    link number by number; a locator that cannot be matched cleanly stays as printed. Returns the html and the
    number of units linked. `lead`: a leading bare number may stand for the locator."""
    if not units:
        return text, 0
    ms = []  # in order; refs name them in order ("Memb. 2 ... Subsect. 1" -> two links)
    for m in LOC.finditer(text):
        s = _trim(m.group(0))
        if s:
            at = m.start() + m.group(0).index(s)
            ms.append((at, at + len(s), s))
    if not ms and lead and (m := LEAD.match(text)):
        ms = [(0, m.end(), m.group(0))]
    if not ms:
        return text, 0
    out, pos, ui = [], 0, 0
    for start, end, s in ms:
        if ui >= len(units):
            break
        out.append(text[pos:start])
        nums = list(re.finditer(r"\d+(?!\d|st|nd|rd|th)", s))
        if len(units) - ui > 1 and len(ms) == 1 and len(nums) == len(units) - ui:
            # "Subsect. 9, 10, 11": each number its own link
            buf, p = [], 0
            for nm in nums:
                buf.append(s[p:nm.start()])
                buf.append(f'<a class="loc" href="{SITE}{attr(units[ui])}/">{nm.group(0)}</a>')
                ui += 1
                p = nm.end()
            buf.append(s[p:])
            out.append("".join(buf))
        else:
            out.append(f'<a class="loc" href="{SITE}{attr(units[ui])}/">{s}</a>')
            ui += 1
        pos = end
    out.append(text[pos:])
    return "".join(out), ui


def node_html(n: dict, by_id: dict, shut: set[str], root: bool = False, d: float = 0) -> str:
    """One node. `d`: its distance from the middle of its parent's brace, so members unfold from the beak outward."""
    nid = n["id"]
    kids = n["children"]
    parts = []
    if n.get("relation") == "or":
        parts.append(f'<p class="or">{esc(n["or"]["text"])}</p>')
    hd = []
    if "head" in n:
        hd.append(f'<span class="colhead">{runs_html(n["head"]["runs"])}</span>')
    text = runs_html(n["text"])
    key = n.get("key")
    if key:
        if key.get("supplied"):
            hd.append(f'<span class="key supplied" title="{attr(key["supplied"])}">[{esc(key["sign"])}]'
                      '<span class="sr-only"> (sign supplied by this edition)</span></span>')
        elif "src_p" in key:
            hd.append(f'<span class="key">{esc(key["text"])}</span>')
        elif text.startswith(esc(key["sign"])):  # the sign printed at the head of the root's own words
            text = f'<span class="key">{esc(key["sign"])}</span>' + text[len(esc(key["sign"])):].lstrip()
    # Where a head links into the book (owner, 2026-11-19: "A is fine"): Burton's words stay as printed, and a small
    # box with the division's number follows them, as the edition does now. (link_locators, which made his own
    # "Subsect. 4" the link, is kept for the record but not used.)
    label = runs_html(n["label"]["runs"]) if "label" in n else ""
    chips, seen = [], []
    for ref in n.get("ref", []):
        if ref["unit"] and ref["unit"] not in seen:
            seen.append(ref["unit"])
            chips.append(f'<a class="syn-ref" href="{SITE}{attr(ref["unit"])}/"><span class="sr-only">to </span>'
                         f'{esc(ref["div"])}</a>')
    for sign, tgt in zip(n.get("see", []), n.get("see_target", []), strict=True):
        i = text.rfind(esc(sign))
        if i >= 0 and text.count("<", 0, i) == text.count(">", 0, i):
            where = " ".join("".join(r["t"] for r in by_id[tgt]["text"]).split()) if tgt in by_id else ""
            text = (text[:i] + f'<a class="see" href="#{attr(tgt)}" title="{attr(where)}">'
                    f'<span class="sr-only">go to the sheet marked </span>{esc(sign)}</a>' + text[i + len(esc(sign)):])
    hd.append(f'<span class="t">{text}</span>')
    if label:
        hd.append(f' <span class="t">{label}</span>')
    if chips:
        hd.append(" " + " ".join(chips))
    if n.get("note"):
        hd.append(f'<span class="ednote" tabindex="0" title="Edition’s note: {attr(n["note"])}">*</span>')
    body = [f'<div class="hd">{"".join(hd)}</div>']
    if kids:
        plain = " ".join("".join(r["t"] for r in n["text"]).split())
        c = count(n)
        body.append(
            f'<div class="kw"><button type="button" class="brace" aria-controls="{attr(nid)}-c" '
            f'aria-expanded="{"false" if nid in shut else "true"}" '
            f'aria-label="{attr(plain)}: open or fold ({c} parts)">'
            f'<span class="ink" aria-hidden="true"></span><span class="cnt" data-n="{c}" aria-hidden="true"></span>'
            '</button>'
            f'<ul class="kids" id="{attr(nid)}-c">'
            + "".join(node_html(k, by_id, shut, d=abs(i - (len(kids) - 1) / 2)) for i, k in enumerate(kids))
            + "</ul></div>")
    cls = "n" + ("" if kids else " leaf") + (" shut" if nid in shut else "") + (" root" if root else "")
    extra = f' data-img="{attr(n["img"])}"' if root and n.get("img") else ""
    return (f'<li class="{cls}" id="{attr(nid)}" data-h="{height(n)}" style="--d:{d:g}"{extra}>{"".join(parts)}'
            f'<div class="nb">{"".join(body)}</div></li>')


def by_ids(tree: dict) -> dict:
    out = {}

    def walk(n):
        out[n["id"]] = n
        for c in n["children"]:
            walk(c)
    for t in tree["children"]:
        walk(t)
    return out


# No ◇ on the synopses (owner, 2026-11-19): the words are all Burton's; the branching's provenance stays in the data.


def tables(part: str, only: list[int] | None = None, shut_roots: bool = False, open_first: bool = True) -> str:
    """One Partition's continuation tables as one list of roots."""
    tree = load(part)
    ids = by_ids(tree)
    roots = tree["children"] if only is None else [tree["children"][i] for i in only]
    shut: set[str] = set()
    for i, r in enumerate(roots):
        if shut_roots and not (open_first and i == 0):
            shut.add(r["id"])
    return "".join(node_html(r, ids, shut, root=True) for r in roots)


ROMAN = {"p1": "I", "p2": "II", "p3": "III"}


def chain(parts: list[str]) -> str:
    """The front page: the three Partitions folded, each opening onto the chain of its sheets. The braces joining
    them are the edition's (drawn lighter); "The Synopses" heads them in one design and is a heading in the other."""
    out = []
    for i, p in enumerate(parts):
        rows = tables(p, shut_roots=True, open_first=False)
        n = len(load(p)["children"])
        d = abs(i - (len(parts) - 1) / 2)
        out.append(f'<li class="n part shut" id="front-{p}" data-h="1" style="--d:{d:g}"><div class="nb">'
                   f'<div class="hd"><span class="key pk">{ROMAN[p]}</span><span class="pt">{esc(PARTS[p])}</span>'
                   f'</div><div class="kw"><button type="button" class="brace ed" aria-controls="front-{p}-c" '
                   f'aria-expanded="false" aria-label="{esc(PARTS[p])}: Burton’s synopsis, {n} sheets: open or fold">'
                   f'<span class="ink" aria-hidden="true"></span>'
                   f'<span class="cnt" data-n="{n}" data-kind="sheets" aria-hidden="true"></span></button>'
                   f'<ul class="kids" id="front-{p}-c">{rows}</ul></div></div></li>')
    return ('<ul class="sheet top chain"><li class="n top-syn" data-h="2"><div class="nb"><div class="hd">'
            '<span class="pt">The Synopses</span></div><div class="kw"><span class="brace ed" aria-hidden="true">'
            f'</span><ul class="kids">{"".join(out)}</ul></div></div></li></ul>')


def stacked(s: str) -> str:
    """The declarations that set a branch's head over its members (R7)."""
    return (f"{s} {{ flex-direction: column; align-items: stretch; }} "
            f"{s} > .hd {{ max-width: none; width: auto; writing-mode: horizontal-tb; transform: none; "
            f"text-align: start; }} "
            f"{s} > .kw {{ margin-left: 0.2em; flex: 0 0 auto; }} "  # in a column, basis 0 would collapse it
            f"{s} > .kw > .brace {{ --bm: var(--m-bracket); }}")


def css_rules() -> str:
    """R7. With script, each branch is measured (data-fit). Without it, a rule per subtree height: a branch needs
    ~11em for its leaves and ~6.2em for each head column."""
    rules = [stacked('.sheet .n[data-fit="stack"] > .nb')]
    for h in range(1, 10):
        sel = f'.sheet:not(.fitted) .n[data-h="{h}"] > .nb'
        rules.append(f"@container (width < {11 + 6.2 * h:g}em) {{ {stacked(sel)} }}")
    return "\n".join(rules)


def main() -> None:
    tpl = (HERE / "proto.html").read_text(encoding="utf-8")
    imgs = {i: f"{SITE}assets/images/{i}" for t in ("p1", "p2", "p3") for i in load(t)["images"]}
    html = (tpl
            .replace("{{SITE}}", SITE)
            .replace("{{CQ}}", css_rules())
            .replace("{{SHEET_A}}", tables("p1", only=[1, 2]))
            .replace("{{OPENING}}", f'<ul class="sheet top">{tables("p1", shut_roots=True)}</ul>')
            .replace("{{OPENING_P2}}", f'<ul class="sheet top">{tables("p2", shut_roots=True)}</ul>')
            .replace("{{FRONT}}", chain(["p1", "p2", "p3"]))
            .replace("{{IMGS}}", json.dumps(imgs)))
    OUT.write_text(html, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
