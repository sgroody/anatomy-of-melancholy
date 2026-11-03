"""Synopsis source text (M7): the hidden tables behind the 20 synopsis images (SURVEY §6).

The images carry the tree; the hidden table carries the words, flattened and partly reordered. The edition takes
the words only from here, verbatim (code points unchanged), and the tree shape from a hand-made structure file
(data/manual/synopses/<pN>.yaml) that names these paragraphs by id. `burton synopses --checklist` writes the
word-level checklist the transcriber works against: state/m7/<pN>-checklist.tsv.
"""

import json
import re

import yaml
from lxml import etree

from .. import paths
from ..fsutil import atomic_write_text
from ..ids import Registry

FILES = {"p1": "chapter001", "p2": "chapter002", "p3": "chapter003"}
GLYPHS = {"⎧", "⎨", "⎩"}  # brace pieces: drawing, not text
OUT = paths.DATA / "synopses"
# Burton's own division labels in a node: "Sect. 2", "Memb. 5", "Subsect. 6, 7, 8" ("Member," is not a label)
PAIR = re.compile(r"\b(Subsect|Sect|Memb)\.\s*(\d+(?:,\s*\d+)*)")
LEVEL = {"sect": 1, "memb": 2, "subsect": 3}


def hidden(part: str) -> list[dict]:
    """The hidden table's paragraphs in document order: id, text (verbatim), and whether it is a brace glyph."""
    d = etree.parse(str(paths.XHTML / f"{FILES[part]}.xhtml"))
    out = []
    for p in (p for t in d.iter("{*}table") for p in t.iter("{*}p")):
        text = "".join(p.itertext())
        out.append({"id": p.get("id"), "text": text, "glyph": text.strip() in GLYPHS})
    return out


def images(part: str) -> list[str]:
    d = etree.parse(str(paths.XHTML / f"{FILES[part]}.xhtml"))
    return [i.get("src").rsplit("/", 1)[-1] for i in d.iter("{*}img") if "penguin_logo" not in i.get("src", "")]


def checklist() -> dict:
    out = {}
    for part in FILES:
        rows = [r for r in hidden(part) if not r["glyph"]]
        dest = paths.STATE / "m7" / f"{part}-checklist.tsv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(dest, "id\ttext\n" + "".join(f"{r['id']}\t{' '.join(r['text'].split())}\n" for r in rows))
        out[part] = {"strings": len(rows), "images": images(part)}
    return out


# ---------------------------------------------------------------- the trees (`burton synopses`)
def paragraphs(part: str) -> dict:
    d = etree.parse(str(paths.XHTML / f"{FILES[part]}.xhtml"))
    return {p.get("id"): p for t in d.iter("{*}table") for p in t.iter("{*}p")}


def runs(p) -> list[dict]:
    """A paragraph's text as runs, code points unchanged: "i" inside <em>, "sym" inside span.arial_bold."""
    flat = []

    def walk(e, i, sym):
        if e.text:
            flat.append([e.text, i, sym])
        for c in e:
            tag = etree.QName(c).localname
            walk(c, i or tag == "em", sym or (tag == "span" and "arial_bold" in (c.get("class") or "")))
            if c.tail:
                flat.append([c.tail, i, sym])

    walk(p, False, False)
    merged = []
    for t, i, sym in flat:
        if merged and merged[-1][1:] == [i, sym]:
            merged[-1][0] += t
        else:
            merged.append([t, i, sym])
    return [{"t": t} | ({"i": True} if i else {}) | ({"sym": True} if sym else {}) for t, i, sym in merged]


def _division(target: list[int], units: list[str]) -> str | None:
    """The unit a division label points to: the subsection itself, or the first unit of a section or member."""
    div = ".".join(map(str, target))
    if len(target) == 4:
        return div if div in units else None
    return next((u for u in units if u.startswith(div + ".")), None)


def resolve(text: str, ctx: list, units: list[str]) -> tuple[list[dict], list]:
    """The division labels in a node's text, resolved against ctx = [partition, sect, memb, subsect] (levels
    a label leaves out are inherited, as a reader of the synopsis does). Returns (refs, ctx after the node).
    Adjacent labels ("Memb. 5 Sect. 2") are one reference. A label whose levels cannot all be known stays
    unresolved (unit null), never guessed."""
    groups: list[dict] = []
    for m in PAIR.finditer(text):
        lvl, nums = LEVEL[m.group(1).lower()], [int(n) for n in m.group(2).split(",")]
        if groups and not text[groups[-1]["end"]:m.start()].strip() and lvl not in groups[-1]["given"]:
            g = groups[-1]
            g["given"][lvl], g["end"], g["label"] = nums, m.end(), text[g["start"]:m.end()]
        else:
            groups.append({"given": {lvl: nums}, "start": m.start(), "end": m.end(), "label": m.group(0)})
    cur, refs = list(ctx), []
    for g in groups:
        given, top, deep = g["given"], min(g["given"]), max(g["given"])
        skipped = any(lv not in given for lv in range(top, deep + 1))
        for n in given[deep]:
            target = [cur[0]] + [given[lv][0] if lv in given else cur[lv] for lv in range(1, deep)] + [n]
            ok = not skipped and None not in target
            refs.append({"label": g["label"], "div": ".".join(str(x) for x in target if x is not None),
                         "unit": _division(target, units) if ok else None})
        cur = cur[:1] + [given[lv][0] if lv in given else cur[lv] for lv in range(1, deep + 1)] + [None] * (3 - deep)
    return refs, cur


def build(part: str, units: list[str], reg: Registry) -> dict:
    """data/synopses/<part>.json from the structure file and the hidden table (words verbatim)."""
    spec = yaml.safe_load((paths.MANUAL / "synopses" / f"{part}.yaml").read_text(encoding="utf-8"))
    paras = paragraphs(part)
    unit = f"{part}-synopsis"
    used: list[str] = []
    see_ctx: dict[str, list] = {}  # cross-key -> context at the node that points to it
    key_root: dict[str, str] = {}  # cross-key -> id of the tree root carrying it
    pending_see: list[dict] = []

    def take(pid: str) -> str:
        if pid not in paras:
            raise SystemExit(f"{part}: {pid} is not a hidden-table paragraph")
        used.append(pid)
        return "".join(paras[pid].itertext())

    def node(n: dict, ctx: list, img: str | None = None) -> tuple[dict, list]:
        text = take(n["p"])
        refs, after = resolve(text, ctx, units)
        out = {"id": reg.assign(unit, "s", f"{FILES[part]}.xhtml#{n['p']}"), "src_p": n["p"],
               "text": runs(paras[n["p"]]), "ref": refs}
        if "or" in n:
            out["relation"] = "or"
            out["or"] = {"src_p": n["or"], "text": take(n["or"])}
        if "key" in n:
            sign = take(n["key"]).strip().rstrip(".")
            out["key"] = {"src_p": n["key"], "text": "".join(paras[n["key"]].itertext()), "sign": sign}
            key_root[sign] = out["id"]
        if "see" in n:
            if n["see"] in see_ctx:
                raise SystemExit(f"{part}: two nodes point to cross-key {n['see']}")
            out["see"] = n["see"]
            see_ctx[n["see"]] = after
            pending_see.append(out)
        if "note" in n:
            out["note"] = " ".join(n["note"].split())
        if img:
            out["img"] = img
        kids, sib = [], after
        for c in n.get("children", []):
            k, sib = node(c, sib)  # later siblings inherit the levels earlier ones set ("Memb. 3." heads a list)
            kids.append(k)
        out["children"] = kids
        return out, after

    base = [int(part[1:]), None, None, None]
    trees: list = [None] * len(spec["trees"])
    todo = list(range(len(spec["trees"])))
    while todo:  # a keyed tree takes its context from the node that points to it, which may come later
        progressed = False
        for i in list(todo):
            t = spec["trees"][i]
            sign = "".join(paras[t["key"]].itertext()).strip().rstrip(".") if "key" in t else None
            if sign is not None and sign not in see_ctx:
                continue
            trees[i], _ = node(t, see_ctx[sign] if sign else base, t.get("img"))
            todo.remove(i)
            progressed = True
        if not progressed:
            raise SystemExit(f"{part}: no node points to the cross-keys of trees {todo}")
    for n in pending_see:
        if n["see"] not in key_root:
            raise SystemExit(f"{part}: cross-key {n['see']} has no tree")
        n["see_target"] = key_root[n["see"]]
    reg.finish_unit(unit)

    dups = []
    for pid, d in (spec.get("duplicates") or {}).items():
        take(pid)
        dups.append({"src_p": pid, "text": "".join(paras[pid].itertext()), "same_as": d["same_as"],
                     "reason": " ".join(d["reason"].split())})
    wanted = [r["id"] for r in hidden(part) if not r["glyph"]]
    if sorted(used) != sorted(wanted):
        missing = sorted(set(wanted) - set(used))
        twice = sorted({u for u in used if used.count(u) > 1})
        raise SystemExit(f"{part}: structure does not use every hidden string once: missing {missing}, twice {twice}")
    return {"id": f"{part}-syn", "part": part, "source": f"{FILES[part]}.xhtml", "images": images(part),
            "provenance": spec["provenance"], "duplicates": dups, "children": trees}


def run(parts: list[str] | None = None) -> dict:
    from .epub import all_units

    units = [u for u in all_units() if u[0].isdigit()]
    reg = Registry()
    out = {}
    for part in parts or FILES:
        if not (paths.MANUAL / "synopses" / f"{part}.yaml").exists():
            out[part] = "no structure file yet"
            continue
        tree = build(part, units, reg)
        atomic_write_text(OUT / f"{part}.json", json.dumps(tree, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        refs = [r for n in walk(tree) for r in n["ref"]]
        out[part] = {"nodes": sum(1 for _ in walk(tree)), "refs": len(refs),
                     "unresolved": [r["label"] for r in refs if r["unit"] is None]}
    reg.save()
    return out


def walk(n: dict):
    for c in n.get("children", []):
        yield c
        yield from walk(c)
