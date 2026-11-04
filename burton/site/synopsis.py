"""The synopsis pages (M7): data/synopses/<pN>.json as a nested, collapsible tree, and the unit -> node map
behind each unit page's "where this stands in the synopsis" link.

Without script the tree is fully open; edition.js adds a disclosure button to every node that has children.
Words are rendered from the tree's runs exactly (italic, symbols, Greek tagged with lang="grc").
"""

import json
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


def runs_html(runs: list[dict]) -> str:
    out = []
    for r in runs:
        t = esc_tagged(r["t"])
        if r.get("sym"):
            t = f'<span class="sym">{t}</span>'
        if r.get("i"):
            t = f"<i>{t}</i>"
        out.append(t)
    return "".join(out)


def _plain(runs: list[dict]) -> str:
    return " ".join("".join(r["t"] for r in runs).split())


def tree_html(tree: dict, root: str, titles: dict[str, str]) -> str:
    """The tree as nested lists. `root` is the relative path to the site root; `titles` maps each built unit to
    its title."""
    by_id = {n["id"]: n for n, _ in _nodes(tree)}

    def node(n: dict) -> str:
        nid = attr(n["id"])
        parts = []
        if "or" in n:
            parts.append(f'<span class="syn-or">{esc(n["or"]["text"])}</span>')
        if "head" in n:
            parts.append(f'<span class="syn-head">{runs_html(n["head"]["runs"])}</span>')
        row = []
        if "key" in n:
            k = n["key"]
            if k.get("supplied"):  # the reason follows the text as an edition's note
                row.append(f'<span class="syn-key syn-supplied" data-resp="editor">{esc(k["sign"])}'
                           '<span class="syn-flag"> (sign supplied by this edition)</span></span> ')
            elif "src_p" in k:
                row.append(f'<span class="syn-key">{esc(k["text"])}</span> ')
        text = runs_html(n["text"])
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
        row.append(f'<span class="syn-t" id="{nid}-t">{text}</span>')
        if "label" in n:
            row.append(f' <span class="syn-label">{runs_html(n["label"]["runs"])}</span>')
        seen = []
        for ref in n.get("ref", []):
            u = ref["unit"]
            if u and u not in seen:
                seen.append(u)
                if u in titles:  # a partial build links only the units it has
                    row.append(f' <a class="syn-ref" href="{root}{attr(u)}/" title="{attr(titles[u])}">'
                               f'<span class="sr-only">to </span>{esc(ref["div"])}</a>')
                else:
                    row.append(f' <span class="syn-ref">{esc(ref["div"])}</span>')
        for sign, tgt in zip(n.get("see", []), n.get("see_target", []), strict=True):
            if tgt in linked:
                continue
            where = _plain(by_id[tgt]["text"]) if tgt in by_id else ""
            row.append(f' <a class="syn-see" href="#{attr(tgt)}" title="{attr(where)}">'
                       f'<span class="sr-only">go to the branch marked </span>{esc(sign)}</a>')
        for note in (n.get("key", {}).get("supplied"), n.get("note")):
            if note:
                row.append(f' <span class="syn-note" data-resp="editor">Edition’s note: {esc(note)}</span>')
        parts.append(f'<div class="syn-row">{"".join(row)}</div>')
        kids = n.get("children", [])
        if kids:
            parts.append(f'<ul class="syn-kids" id="{nid}-c">' + "".join(node(c) for c in kids) + "</ul>")
        rel = ' data-rel="or"' if n.get("relation") == "or" else ""
        return f'<li class="syn-n" id="{nid}"{rel}>{"".join(parts)}</li>'

    return '<ul class="syn-tree">' + "".join(node(t) for t in tree["children"]) + "</ul>"


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


def label(tree: dict) -> Markup:
    p = tree["provenance"]
    review = (f"checked against the sheets by the {esc(p['checked_by'])} ({esc(p['checked_date'])})"
              if p.get("status") == "checked" else "not yet reviewed")
    return Markup(f'Branching read from the printed sheets by {esc(p["model"])} ({esc(p["by"])}, {esc(p["date"])}), '
                  f"{review}. The words are Burton’s, taken verbatim from the source’s text of the sheets.")
