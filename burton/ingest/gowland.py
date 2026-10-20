"""Separate Gowland's editorial matter: [translations] -> ed:trans, {interpolations} -> supplied.

The bracket characters stay inside the wrappers, so no text is lost or altered. Pairs are matched
within one element's mixed content; a bracket that cannot be matched at its own level is counted
as an anomaly and left alone (never guessed).
"""

from collections import Counter

from ..tei import ED, T, el, is_ed, local, put_items, take_items

SKIP = {ED("verse-trans"), ED("block"), T("pb"), ED("enref"), T("lb")}


def _wrap_pairs(e, opener: str, closer: str, make, stats: Counter, key: str) -> None:
    items = take_items(e)
    out: list = []
    pending: list | None = None  # items collected since an unmatched opener
    depth = 0
    for it in items:
        if not isinstance(it, str):
            (pending if pending is not None else out).append(it)
            continue
        buf = ""
        for ch in it:
            if pending is None:
                if ch == opener:
                    if buf:
                        out.append(buf)
                    buf = ch
                    pending, depth = [], 1
                else:
                    buf += ch
            else:
                buf += ch
                if ch == opener:
                    depth += 1
                elif ch == closer:
                    depth -= 1
                    if depth == 0:
                        pending.append(buf)
                        w = make()
                        put_items(w, pending)
                        out.append(w)
                        stats[key] += 1
                        pending, buf = None, ""
        if buf:
            (pending if pending is not None else out).append(buf)
    if pending is not None:  # unmatched opener: restore the content untouched
        stats[f"{key}:unmatched-open"] += 1
        out.extend(pending)
    put_items(e, out)
    # a closer with no opener at this level
    for it in out:
        if isinstance(it, str) and closer in it:
            stats[f"{key}:unmatched-close"] += 1


def _walk(e, stats: Counter, *, brackets: bool) -> None:
    if e.tag == T("supplied"):
        return  # already a wrapped {…}; its own braces must not be wrapped again
    if e.tag in SKIP:
        if e.tag == ED("verse-trans"):
            stats["verse-trans"] += 1
            for c in e.iter(T("l")):  # braces inside Gowland's verse are still his
                _wrap_pairs(c, "{", "}", lambda: el("supplied", {"resp": "#gowland"}), stats, "supplied")
        return
    if brackets:
        _wrap_pairs(e, "[", "]", lambda: el(ED("trans")), stats, "trans")
    _wrap_pairs(e, "{", "}", lambda: el("supplied", {"resp": "#gowland"}), stats, "supplied")
    for c in list(e):
        if not isinstance(c.tag, str):
            continue
        # inside a Gowland translation only braces remain to be marked
        _walk(c, stats, brackets=brackets and c.tag != ED("trans"))


def separate(div) -> Counter:
    stats: Counter = Counter()
    _walk(div, stats, brackets=True)
    _join_blocks(div, stats)
    return +stats  # drop the unmatched counters that the block pass brought back to zero


# ---------------------------------------------------------------- translations running over blocks
# Gowland sometimes translates a long Latin passage in one bracket that runs over several paragraphs,
# with the verse it quotes (also his translation) set as block quotes in between. Within one
# container (div, quote, sidenote), when a paragraph is left with one unmatched '[' in its own text,
# the following blocks have no unmatched bracket, and a later paragraph has one unmatched ']' in its
# own text, the whole run is his. Each piece is wrapped where it lies (ed:trans@part I/M/F, an
# intermediate verse group as ed:verse-trans@part=M), so the block structure is unchanged. As with a
# bracket inside one paragraph, sidenotes anchored inside the run go in with it: they are Gowland's
# English renderings of Burton's Latin sidenotes, which stand at the Latin before the bracket.
# Anything less regular stays unmatched (and V8t fails).

CONTAINERS = (T("div"), T("quote"), T("note"))


def _brackets(s: str | None) -> list[str]:
    return [ch for ch in s or "" if ch in "[]"]


def _own(e) -> list[str]:
    """Unmatched brackets in e's own mixed content (matched pairs are already wrapped)."""
    return _brackets(e.text) + [ch for c in e for ch in _brackets(c.tail)]


def _deep(e) -> list[str]:
    """Unmatched brackets anywhere in e, outside Gowland's matter and sidenotes."""
    out: list[str] = []

    def walk(x):
        if x is e or not (x.tag == T("note") or is_ed(x) or x.tag == T("supplied")):
            out.extend(_brackets(x.text))
            for c in x:
                walk(c)
        if x is not e:
            out.extend(_brackets(x.tail))

    walk(e)
    return out


def _wholly_wrappable(b) -> bool:
    if b.tag == T("p"):
        return True
    return b.tag == T("quote") and all(_wholly_wrappable(c) or c.tag in (T("lg"), ED("verse-trans")) for c in b)


def _run_end(kids: list, i: int) -> int | None:
    first = kids[i]
    if first.tag != T("p") or _own(first) != ["["] or _deep(first) != ["["]:
        return None
    for k in range(i + 1, len(kids)):
        b = kids[k]
        found = _deep(b)
        if not found and _wholly_wrappable(b):
            continue
        if found == ["]"] and _own(b) == ["]"] and b.tag == T("p"):
            return k
        return None
    return None


def _has_text(items: list) -> bool:
    return any((it.strip() if isinstance(it, str) else
                not is_ed(it) and it.tag != T("pb") and "".join(it.itertext()).strip()) for it in items)


def _wrap(items: list, part: str, stats: Counter) -> list:
    if not _has_text(items):
        return items
    w = el(ED("trans"), {"part": part})
    put_items(w, items)
    stats["trans:piece"] += 1
    return [w]


def _split_at(e, ch: str) -> tuple[list, list]:
    """e's items split just before the only '[' (or just after the only ']') in its own text."""
    items = take_items(e)
    for n, it in enumerate(items):
        if isinstance(it, str) and ch in it:
            k = it.index(ch) + (ch == "]")
            return items[:n] + [it[:k]], [it[k:]] + items[n + 1:]
    raise AssertionError(f"no {ch!r} in own text")


def _wrap_whole(b, stats: Counter) -> None:
    if b.tag == T("p"):
        put_items(b, _wrap(take_items(b), "M", stats))
        return
    for c in list(b):  # a quote
        if c.tag == ED("verse-trans"):
            continue  # already his
        if c.tag == T("lg"):
            w = el(ED("verse-trans"), {"part": "M"})
            b.replace(c, w)
            w.append(c)
            c.attrib.pop("type", None)
            stats["verse-trans"] += 1
        else:
            _wrap_whole(c, stats)


def _join_blocks(div, stats: Counter) -> None:
    for c in list(div.iter(*CONTAINERS)):
        if any(is_ed(a) or a.tag == T("supplied") for a in c.iterancestors()):
            continue  # inside Gowland's matter (possibly wrapped by an earlier run)
        kids = [k for k in c if isinstance(k.tag, str)]
        i = 0
        while i < len(kids):
            end = _run_end(kids, i)
            if end is None:
                i += 1
                continue
            before, after = _split_at(kids[i], "[")
            put_items(kids[i], before + _wrap(after, "I", stats))
            for b in kids[i + 1:end]:
                _wrap_whole(b, stats)
            head, rest = _split_at(kids[end], "]")
            put_items(kids[end], _wrap(head, "F", stats) + rest)
            stats["trans"] += 1
            stats["trans:across-blocks"] += 1
            stats["trans:unmatched-open"] -= 1
            stats["trans:unmatched-close"] -= 1
            i = end + 1


def trans_without_foreign(div) -> list:
    """ed:trans elements whose preceding sibling is not a foreign passage (for the review list).
    Continuation pieces of a translation running over blocks (@part M/F) are not listed."""
    out = []
    for t in div.iter(ED("trans")):
        if t.get("part") in ("M", "F"):
            continue
        prev = t.getprevious()
        between = (prev.tail if prev is not None else t.getparent().text) or ""
        last = prev[-1] if prev is not None and len(prev) else None
        ok = (prev is not None and between.strip(" ,;:.") == ""
              and (local(prev.tag) == "foreign" or prev.get("ana") == "foreign"
                   or (last is not None and last.get("ana") == "foreign"
                       and not (last.tail or "").strip(" ,;:."))))
        if not ok:
            out.append(t)
    return out
