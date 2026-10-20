"""Plain-text views of the base text for models and checks that must never see Gowland's matter.

`public_text` drops every ed:* element and every supplied[@resp=#gowland] (CLAUDE.md rule 5:
Gowland's editorial matter is never sent to a model). Sidenotes are dropped by default.
"""

import re

from .tei import ED_NS, XML_ID, T


def is_gowland(e) -> bool:
    return (isinstance(e.tag, str) and e.tag.startswith(f"{{{ED_NS}}}")) or \
        (e.tag == T("supplied") and e.get("resp") == "#gowland") or e.tag == T("pb")


def public_text(e, *, notes: bool = False, mark: str | None = None, sep: str = " ",
                note_marker: str | None = None) -> str:
    """Text of `e` without Gowland's matter. If `mark` is an xml:id, that element is wrapped ⟦…⟧.
    If `note_marker` is a note's xml:id, that (otherwise omitted) note shows as "⟦sidenote⟧"."""
    out: list[str] = []

    def walk(x):
        if is_gowland(x):
            pass
        elif x.tag == T("note") and note_marker is not None and x.get(XML_ID) == note_marker:
            out.append("⟦sidenote⟧")
        elif x.tag == T("note") and not notes and x is not e:
            pass
        else:
            open_ = mark is not None and x.get(XML_ID) == mark
            if open_:
                out.append("⟦")
            if x.tag == T("l") and out and x.getprevious() is not None:
                out.append(" / ")
            elif x.tag in (T("l"), T("p"), T("head"), T("lg")) and out:
                out.append(sep)
            if x.text:
                out.append(x.text)
            for c in x:
                walk(c)
            if open_:
                out.append("⟧")
        if x.tail and x is not e:
            out.append(x.tail)

    walk(e)
    text = " ".join("".join(out).split())
    return re.sub(r" ([,;:.)])", r"\1", text)  # spaces left where Gowland's brackets were removed


def notes_in(e) -> list:
    return [n for n in e.iter(T("note"))]
