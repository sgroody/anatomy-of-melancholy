"""The synopses: data/synopses/<pN>.json set as Burton's sheets (braces read left to right), and the unit -> node
map behind each unit page's "where this stands in the synopsis" link.

Without script every brace is open; edition.js fits the sheet to its width, folds the braces marked to start folded,
and opens a folded brace when the reader rests on it or clicks it. Words are rendered from the tree's runs exactly
(italic, symbols, Greek tagged with lang="grc").
"""

import json
import re
from functools import cache

from markupsafe import Markup

from .. import paths
from .render import attr, esc, esc_tagged


@cache
def load(part: str) -> dict | None:
    f = paths.DATA / "synopses" / f"{part}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def _nodes(n: dict, depth: int = 0):
    for c in n.get("children", []):
        yield c, depth
        yield from _nodes(c, depth + 1)


# the astrological and alchemical signs in Burton's words (the planets in "under ♄"), set in rubric like the keys
# (owner, 2026-11-20: "not all the alchemical symbols on the front page synopses are properly red")
SIGNS = re.compile("([☉☽-♓⊕🜀-🝿]+)")


def runs_html(runs: list[dict]) -> str:
    out = []
    for r in runs:
        t = esc_tagged(r["t"])
        if r.get("sym"):
            t = f'<span class="sym">{t}</span>'
        else:
            t = SIGNS.sub(lambda m: f'<span class="sym">{m.group(1)}</span>', t)
        if r.get("i"):
            t = f"<i>{t}</i>"
        out.append(t)
    return "".join(out)


ROMAN = {"p1": "I", "p2": "II", "p3": "III"}


def _plain(runs: list[dict]) -> str:
    return " ".join("".join(r["t"] for r in runs).split())


def _height(n: dict) -> int:
    """Levels below a node (a leaf is 0): the starting value for the sheet's width rules."""
    return 1 + max(map(_height, n["children"])) if n.get("children") else 0


def _count(n: dict) -> int:
    return sum(1 + _count(c) for c in n.get("children", []))


def tree_html(tree: dict, root: str, titles: dict[str, str], fold: str = "none") -> str:
    """The synopsis as Burton's sheet (2026-11-19, from tools/synopsis_sheets): each node a head beside a drawn
    brace holding its members, read left to right; edition.js fits the sheet to its width branch by branch (a head
    set over its members where there is no room, a tall head turned, as the printer did) and folds and opens the
    braces. `root` is the relative path to the site root; `titles` maps each built unit to its title.

    fold: "none", every brace open (the synopsis pages); "sheets", the first sheet open and the later ones folded to
    their opening lines (the head of a Partition's first page). A folded branch is only marked (data-fold); the
    script folds it, so without script the whole sheet is open."""
    by_id = {n["id"]: n for n, _ in _nodes(tree)}
    roots = tree["children"]
    shut = {r["id"] for r in roots[1:]} if fold == "sheets" else set()
    rows = "".join(_node(r, by_id, root, titles, shut, is_root=True) for r in roots)
    return f'<ul class="syn-sheet">{rows}</ul>'


def _node(n: dict, by_id: dict, root: str, titles: dict[str, str], shut: set[str], is_root: bool = False,
          d: float = 0) -> str:
    """One node. `d`: its distance from the middle of its parent's brace, so members unfold from the beak outward."""
    nid = attr(n["id"])
    kids = n.get("children", [])
    hd = []
    if "head" in n:  # a column heading printed above ("Memb.", "Subsect.")
        hd.append(f'<span class="syn-head">{runs_html(n["head"]["runs"])}</span>')
    text = runs_html(n["text"])
    if "key" in n:
        k = n["key"]
        if k.get("supplied"):
            hd.append(f'<span class="syn-key syn-supplied" data-resp="editor" title="{attr(k["supplied"])}">'
                      f'[{esc(k["sign"])}]<span class="sr-only"> (sign supplied by this edition)</span></span>')
        elif "src_p" in k:
            hd.append(f'<span class="syn-key">{esc(k["text"])}</span>')
        else:  # the sign printed at the head of the root's own words: its column
            for lead in (esc(k["sign"]), f'<span class="sym">{esc(k["sign"])}</span>'):
                if text.startswith(lead):
                    text = f'<span class="syn-key">{esc(k["sign"])}</span>' + text[len(lead):].lstrip()
                    break
    linked = set()
    for sign, tgt in zip(n.get("see", []), n.get("see_target", []), strict=True):
        # the sign Burton prints ("See ♋ ♌ ♍") is itself the link (owner, 2026-11-03), not a copy after it
        i = text.find(esc(sign))
        if i >= 0 and "<" not in text[i:i + len(esc(sign))] and text.count("<", 0, i) == text.count(">", 0, i):
            where = _plain(by_id[tgt]["text"]) if tgt in by_id else ""
            text = (text[:i] + f'<a class="syn-see" href="#{attr(tgt)}" title="{attr(where)}">'
                    f'<span class="sr-only">go to the branch marked </span>{esc(sign)}</a>'
                    + text[i + len(esc(sign)):])
            linked.add(tgt)
    hd.append(f'<span class="syn-t" id="{nid}-t">{text}</span>')
    if "label" in n:
        hd.append(f' <span class="syn-label">{runs_html(n["label"]["runs"])}</span>')
    # where a head names a part of the book, the small box with its number follows Burton's words and is the link
    # (owner, 2026-11-19: "A is fine")
    seen = []
    for ref in n.get("ref", []):
        u = ref["unit"]
        if u and u not in seen:
            seen.append(u)
            if u in titles:  # a partial build links only the units it has
                hd.append(f' <a class="syn-ref" href="{root}{attr(u)}/" title="{attr(titles[u])}">'
                          f'<span class="sr-only">to </span>{esc(ref["div"])}</a>')
            else:
                hd.append(f' <span class="syn-ref">{esc(ref["div"])}</span>')
    for sign, tgt in zip(n.get("see", []), n.get("see_target", []), strict=True):
        if tgt in linked:
            continue
        where = _plain(by_id[tgt]["text"]) if tgt in by_id else ""
        hd.append(f' <a class="syn-see" href="#{attr(tgt)}" title="{attr(where)}">'
                  f'<span class="sr-only">go to the branch marked </span>{esc(sign)}</a>')
    if n.get("note"):
        note = esc(n["note"])
        hd.append(f'<span class="syn-note" data-resp="editor" tabindex="0" title="Edition’s note: {attr(n["note"])}">'
                  f'*<span class="sr-only"> Edition’s note: {note}</span></span>')
    body = [f'<div class="syn-hd">{"".join(hd)}</div>']
    if kids:
        c = _count(n)
        members = "".join(_node(k, by_id, root, titles, shut, d=abs(i - (len(kids) - 1) / 2))
                          for i, k in enumerate(kids))
        body.append(f'<div class="syn-kw"><button type="button" class="syn-brace" aria-controls="{nid}-c" '
                    f'aria-expanded="true" aria-label="{attr(_plain(n["text"]))}: open or fold ({c} parts)">'
                    '<span class="syn-ink" aria-hidden="true"></span><span class="syn-cnt" aria-hidden="true"></span>'
                    f'</button><ul class="syn-kids" id="{nid}-c">{members}</ul></div>')
    cls = "syn-n" + ("" if kids else " syn-leaf") + (" syn-root" if is_root else "")
    fold = ' data-fold="shut"' if n["id"] in shut else ""
    rel = ' data-rel="or"' if n.get("relation") == "or" else ""
    orp = f'<p class="syn-or">{esc(n["or"]["text"])}</p>' if n.get("relation") == "or" and "or" in n else ""
    return (f'<li class="{cls}" id="{nid}" data-h="{_height(n)}" style="--d:{d:g}"{fold}{rel}>{orp}'
            f'<div class="syn-nb">{"".join(body)}</div></li>')


def front_html(parts: list[tuple[str, str, dict]], root: str, titles: dict[str, str]) -> str:
    """The front page (owner, 2026-11-19): the three Partitions folded, each keyed with a rubric numeral; resting on
    a name opens it onto the chain of its sheets, each folded to its opening line. The brackets joining a Partition to
    its sheets are the edition's, drawn lighter. parts: (key, title, tree)."""
    out = []
    for i, (key, title, tree) in enumerate(parts):
        by_id = {n["id"]: n for n, _ in _nodes(tree)}
        roots = tree["children"]
        rows = "".join(_node(r, by_id, root, titles, {r["id"] for r in roots}, is_root=True) for r in roots)
        d = abs(i - (len(parts) - 1) / 2)
        k = attr(key)
        out.append(
            f'<li class="syn-n syn-part" id="front-{k}" data-h="1" style="--d:{d:g}" data-fold="shut">'
            f'<div class="syn-nb"><div class="syn-hd"><span class="syn-key syn-pk">{ROMAN.get(key, "")}</span>'
            f'<span class="syn-pt">{esc(title)}</span></div><div class="syn-kw"><button type="button" '
            f'class="syn-brace syn-ed" aria-controls="front-{k}-c" aria-expanded="true" '
            f'aria-label="{attr(title)}: Burton’s synopsis, {len(roots)} sheets: open or fold">'
            '<span class="syn-ink" aria-hidden="true"></span><span class="syn-cnt" aria-hidden="true"></span>'
            f'</button><ul class="syn-kids" id="front-{k}-c">{rows}</ul></div></div></li>')
    return f'<ul class="syn-sheet syn-front">{"".join(out)}</ul>'


def back_links(parts: list[str], units: list[str]) -> dict[str, tuple[str, str]]:
    """unit -> (partition, node id) of the node that best stands for it: a label naming the subsection itself;
    else the label of the member, then the section, it belongs to (3.2.1.2 has no head of its own, so it links
    to "Memb. 1."); among equals the deepest node, then the first."""
    best: dict[str, tuple] = {}
    for part in parts:
        tree = load(part)
        if not tree:
            continue
        for order, (n, depth) in enumerate(_nodes(tree)):
            for ref in n.get("ref", []):
                if not ref["unit"]:
                    continue
                for u in units:
                    if u == ref["div"] or u.startswith(ref["div"] + "."):
                        rank = (4 - ref["div"].count("."), -depth, order)  # subsection 1, member 2, section 3
                        if u not in best or rank < best[u][0]:
                            best[u] = (rank, part, n["id"])
    return {u: (p, nid) for u, (_, p, nid) in best.items()}


LOCATORS = re.compile(r"^(?:(?:Part|Sect|Memb|Subsect|Subs)\.?\s*\d+\.?\s*)+")
CUR = 'class="sb-cur" aria-current="page"'


def short(text: str, words: int = 4) -> str:
    """A node's label cut to its first clause, without Burton's locators: "Memb. 3 Sect. 2. Passions and perturbations
    of the mind, Subsect. 1 …" -> "Passions and perturbations of the …"."""
    t = LOCATORS.sub("", text).strip()
    t = re.split(r"[,.;:(]", t, maxsplit=1)[0].strip() or t
    w = t.split()
    return " ".join(w[:words]) + ("…" if len(w) > words else "")


def branch_html(unit: str, part: str, nid: str, root: str, titles: dict[str, str]) -> str:
    """Where a page stands in Burton's synopsis (owner, 2026-11-04: N1 D): a small mark at the top left naming the
    Partition and the branches above the page; pointing at it (or focusing it) opens the path, each step linked to its
    node in the synopsis, and the sections the page's node names, the page's own in red, each linked to its page."""
    def find(n, trail):
        for c in n.get("children", []):
            if c["id"] == nid:
                return trail + [c]
            if r := find(c, trail + [c]):
                return r
        return None

    path = find(load(part), []) or []
    if not path:
        return ""
    syn = f"{root}{part}/synopsis/"
    here = short(titles.get(unit, unit), 3)
    # the last step is the node that stands for this page; it often names several sections ("Sorrow … Discontents"),
    # so it is labelled with the page's own title
    labels = [short(_plain(n.get("text", []))) for n in path[:-1]] + [here]
    line = " · ".join([ROMAN.get(part, part), *[esc_tagged(x) for x in labels[-3:-1]],
                       f'<span class="sb-cur">{esc_tagged(here)}</span>'])
    steps = "".join(f'<a class="sb-step{" syn-node" if n is path[-1] else ""}" style="--d:{k}" '
                    f'href="{attr(syn)}#{attr(n["id"])}">{esc_tagged(lab)}</a>'
                    for k, (n, lab) in enumerate(zip(path, labels, strict=True)))
    units = [r["unit"] for r in path[-1].get("ref", []) if r.get("unit") and r["unit"] in titles]
    sibs = " · ".join(f'<a href="{root}{attr(u)}/"{chr(32) + CUR if u == unit else ""}>'
                      f'{esc_tagged(short(titles[u], 3))}</a>' for u in dict.fromkeys(units))
    return (f'<div class="syn-badge" tabindex="0" aria-label="Where this page stands in Burton’s synopsis">'
            f'<span class="sb-ico" aria-hidden="true">{{</span><span class="sb-line">{line}</span>'
            f'<div class="sb-pop">{steps}{f"<p class=\"sb-sibs\">{sibs}</p>" if sibs else ""}'
            f'<a class="sb-all" href="{attr(syn)}">The whole synopsis of Partition {ROMAN.get(part, part)}</a>'
            '</div></div>')


def label(tree: dict) -> Markup:
    p = tree["provenance"]
    review = (f"checked against the sheets by the {esc(p['checked_by'])} ({esc(p['checked_date'])})"
              if p.get("status") == "checked" else "not yet reviewed")
    return Markup(f'Branching read from the printed sheets by {esc(p["model"])} ({esc(p["by"])}, {esc(p["date"])}), '
                  f"{review}. The words are Burton’s, taken verbatim from the source’s text of the sheets.")
