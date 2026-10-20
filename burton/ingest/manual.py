"""Apply hand-made block-level decisions from data/manual/blocks.yaml (markup only, never text)."""

from collections import Counter
from functools import cache

import yaml

from .. import paths
from ..tei import ED, XML_LANG, T, el


@cache
def blocks() -> dict:
    return yaml.safe_load((paths.MANUAL / "blocks.yaml").read_text(encoding="utf-8")) or {}


def _top_index(div, epub_id: str) -> int:
    """Index of the top-level block of `div` that is, or contains, the EPUB element `epub_id`."""
    kids = [k for k in div if isinstance(k.tag, str)]
    for i, k in enumerate(kids):
        for e in k.iter():
            if isinstance(e.tag, str) and (e.get("src") or "").endswith(f"#{epub_id}"):
                return i
    raise LookupError(f"blocks.yaml: {epub_id} not found in unit {div.get('n')}")


def _range(div, spec: dict) -> list:
    kids = [k for k in div if isinstance(k.tag, str)]
    a = _top_index(div, spec["from"])
    b = len(kids) - 1 if spec["to"] == "END" else _top_index(div, spec["to"])
    if b < a:
        raise ValueError(f"blocks.yaml: empty range {spec}")
    return kids[a:b + 1]


def _wrap(div, members: list, wrapper) -> None:
    div.insert(div.index(members[0]), wrapper)
    wrapper.tail = members[-1].tail
    for m in members:
        wrapper.append(m)


def apply(div, unit: str) -> Counter:
    stats: Counter = Counter()
    data = blocks()
    for spec in (s for s in data.get("gowland", []) if s["unit"] == unit):
        members = _range(div, spec)
        _wrap(div, members, el(ED("block")))
        stats["gowland-block"] += 1
    for spec in (s for s in data.get("language", []) if s["unit"] == unit):
        attrs = {XML_LANG: spec["lang"], "ana": "foreign", "resp": "#editor", "cert": "high"}
        if "head" in spec:
            head = div[_top_index(div, spec["head"])]
            if head.tag != T("head"):
                raise ValueError(f"blocks.yaml: {spec['head']} is not a heading")
            for k, v in attrs.items():
                head.set(k, v)
            stats["language-head"] += 1
            continue
        members = _range(div, spec)
        if len(members) == 1 and members[0].tag == T("lg"):
            for k, v in attrs.items():
                members[0].set(k, v)
        else:
            _wrap(div, members, el("quote", {"type": "block", **attrs}))
        stats["language-block"] += 1
    return stats


@cache
def source_fixes() -> list:
    return yaml.safe_load((paths.MANUAL / "source-fixes.yaml").read_text(encoding="utf-8")) or []


def apply_fixes(div, unit: str) -> Counter:
    """Insert <choice><sic/><corr/></choice> for recorded source defects; the original text stays in sic."""
    from ..tei import put_items, take_items

    stats: Counter = Counter()
    for fx in (f for f in source_fixes() if f["unit"] == unit):
        hosts = [e for e in div.iter() if isinstance(e.tag, str) and (e.get("src") or "").endswith(f"#{fx['in']}")]
        if len(hosts) != 1:
            raise LookupError(f"source-fixes.yaml: {fx['in']} found {len(hosts)} times in {unit}")
        done = False
        for owner in hosts[0].iter():
            if not isinstance(owner.tag, str):
                continue
            items = take_items(owner)
            out = []
            for it in items:
                if isinstance(it, str) and not done and it.count(fx["phrase"]) == 1:
                    before, after = it.split(fx["phrase"])
                    a, b = fx["phrase"].split(fx["sic"], 1)
                    choice = el("choice")
                    choice.append(el("sic", text=fx["sic"]))
                    choice.append(el("corr", {"resp": "#editor"}, fx["corr"]))
                    if fx.get("lang"):  # the whole phrase becomes one foreign passage
                        holder = el("foreign", {XML_LANG: fx["lang"], "ana": "foreign", "resp": "#editor",
                                                "cert": "high"})
                        put_items(holder, [a, choice, b])
                        out += [before, holder, after]
                    else:
                        out += [before + a, choice, b + after]
                    done = True
                else:
                    out.append(it)
            put_items(owner, out)
            if done:
                break
        if not done:
            raise LookupError(f"source-fixes.yaml: phrase {fx['phrase']!r} not found once in {fx['in']}")
        stats["source-fix"] += 1
    return stats
