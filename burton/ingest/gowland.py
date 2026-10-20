"""Separate Gowland's editorial matter: [translations] -> ed:trans, {interpolations} -> supplied.

The bracket characters stay inside the wrappers, so no text is lost or altered. Pairs are matched
within one element's mixed content; a bracket that cannot be matched at its own level is counted
as an anomaly and left alone (never guessed).
"""

from collections import Counter

from ..tei import ED, T, el, local, put_items, take_items

SKIP = {ED("verse-trans"), T("pb"), ED("enref"), T("lb")}


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
    return stats


def trans_without_foreign(div) -> list:
    """ed:trans elements whose preceding sibling is not a foreign passage (for the review list)."""
    out = []
    for t in div.iter(ED("trans")):
        prev = t.getprevious()
        between = (prev.tail if prev is not None else t.getparent().text) or ""
        ok = (prev is not None and between.strip(" ,;:.") == ""
              and (local(prev.tag) == "foreign" or prev.get("ana") == "foreign"))
        if not ok:
            out.append(t)
    return out
