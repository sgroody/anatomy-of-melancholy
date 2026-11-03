"""Webster's Revised Unabridged Dictionary (1913), Project Gutenberg #29765 (public domain in the USA),
read by rule for the obsolete-word glosses (M8, D6). Pinned in data/source/WEBSTER.lock.

An entry is a headword line in capitals, a line with the syllabified word, part of speech and
etymology, then senses: "Defn: …" or "1. …", "2. …". A sense's usage labels are in brackets
("[Obs.]", "[Archaic]", "[R.]"); an authority's name may follow ("Burton.").
"""

import hashlib
import re
from dataclasses import dataclass, field
from functools import cache

from .. import paths

FILE = paths.SOURCE / "webster" / "29765.txt.utf-8"
LOCK = paths.SOURCE / "WEBSTER.lock"
HEAD = re.compile(r"^[A-Z][A-Z'\- ]*$")
SENSE = re.compile(r"^(?:Defn: |(\d+)\. (?:\([^)]*\) )?)(.*)")
OBS = re.compile(r"\[(?:Obs\.|Archaic|Obs\. or Archaic|Obs\. or R\.|Archaic or Obs\.)[^\]]*\]")
POS = re.compile(r",\s*(n|a|adv|v\. t|v\. i|v|prep|conj|interj|p\. p|p\. a|pron)\.")


@dataclass
class Entry:
    head: str  # lower case
    pos: str | None
    senses: list[str] = field(default_factory=list)  # each sense's text, labels and authorities included
    heads: list[str] = field(default_factory=list)  # each sense's first lines: its definition and label

    def obsolete(self) -> list[int]:
        """Senses labelled obsolete or archaic in their definition (the first three lines), not merely in a
        phrase quoted under them ("Not . . . but, only. [Obs. or Colloq.]" under the common adverb)."""
        return [i for i, h in enumerate(self.heads) if OBS.search(h)]


def check_lock() -> None:
    want = next(ln.split()[0] for ln in LOCK.read_text(encoding="utf-8").splitlines() if ln and ln[0] != "#")
    have = hashlib.sha256(FILE.read_bytes()).hexdigest()
    if have != want:
        raise SystemExit(f"{FILE.name}: sha256 {have[:12]}… does not match WEBSTER.lock ({want[:12]}…)")


@cache
def entries() -> dict[str, list[Entry]]:
    """Headword (lower case) -> its entries, in the dictionary's order."""
    check_lock()
    text = FILE.read_text(encoding="utf-8")
    body = text.split("*** START OF", 1)[1].split("\n", 1)[1].split("*** END OF", 1)[0]
    lines = body.split("\n")
    out: dict[str, list[Entry]] = {}
    cur: Entry | None = None
    buf: list[str] | None = None

    def flush():
        if cur is not None and buf:
            cur.senses.append(" ".join(" ".join(buf).split()))
            cur.heads.append(" ".join(" ".join(buf[:3]).split()))

    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if HEAD.match(ln) and nxt and not nxt.startswith(("Defn:", " ")) and nxt[:1].isalpha():
            flush()
            m = POS.search(nxt)
            cur, buf = Entry(ln.lower(), m.group(1) if m else None), None
            out.setdefault(cur.head, []).append(cur)
            i += 2
            continue
        m = SENSE.match(ln)
        if cur is not None and m:
            flush()
            buf = [m.group(2)]
        elif cur is not None and buf is not None:
            if ln:
                buf.append(ln)
            else:
                flush()
                buf = None
        i += 1
    flush()
    return out


def wholly_obsolete(word: str) -> list[Entry] | None:
    """The word's entries if every sense of every entry is labelled obsolete or archaic, else None."""
    es = entries().get(word.lower())
    if not es or not all(e.senses for e in es):
        return None
    if all(len(e.obsolete()) == len(e.senses) for e in es):
        return es
    return None


def clean_sense(s: str) -> str:
    """A sense as shown: its own words, without usage labels, quotations or authorities after them."""
    s = OBS.split(s, 1)[0]
    s = re.sub(r"\[[^\]]*\]", "", s)
    return " ".join(s.split()).rstrip(" ;,")
