"""The King James Version, for the Bible verses in the margin (stage 6): Project Gutenberg #10 and its Apocrypha,
#124, pinned in data/source/KJV.lock.

Each book begins at its title line; a title is taken only where text stands between it and the book before it, since
a subtitle can repeat a later book's title ("The First Book of Samuel / Otherwise Called: The First Book of the
Kings"). Verses are `C:V text`, sometimes several on a line. Book ids are data/abbreviations.yaml's; a numbered book
needs its number (`book_n` in the citation layers), and a book that takes one is never looked up without it.
"""

import hashlib
import re
from functools import cache

from .. import paths

DIR = paths.DATA / "source" / "kjv"
LOCK = paths.DATA / "source" / "KJV.lock"

# the title lines of the books, in the order they stand in each file
OT_NT = ["The First Book of Moses: Called Genesis", "The Second Book of Moses: Called Exodus",
         "The Third Book of Moses: Called Leviticus", "The Fourth Book of Moses: Called Numbers",
         "The Fifth Book of Moses: Called Deuteronomy", "The Book of Joshua", "The Book of Judges", "The Book of Ruth",
         "The First Book of Samuel", "The Second Book of Samuel", "The First Book of the Kings",
         "The Second Book of the Kings", "The First Book of the Chronicles", "The Second Book of the Chronicles",
         "Ezra", "The Book of Nehemiah", "The Book of Esther", "The Book of Job", "The Book of Psalms", "The Proverbs",
         "Ecclesiastes", "The Song of Solomon", "The Book of the Prophet Isaiah", "The Book of the Prophet Jeremiah",
         "The Lamentations of Jeremiah", "The Book of the Prophet Ezekiel", "The Book of Daniel", "Hosea", "Joel",
         "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
         "The Gospel According to Saint Matthew", "The Gospel According to Saint Mark",
         "The Gospel According to Saint Luke", "The Gospel According to Saint John", "The Acts of the Apostles",
         "The Epistle of Paul the Apostle to the Romans", "The First Epistle of Paul the Apostle to the Corinthians",
         "The Second Epistle of Paul the Apostle to the Corinthians",
         "The Epistle of Paul the Apostle to the Galatians",
         "The Epistle of Paul the Apostle to the Ephesians", "The Epistle of Paul the Apostle to the Philippians",
         "The Epistle of Paul the Apostle to the Colossians",
         "The First Epistle of Paul the Apostle to the Thessalonians",
         "The Second Epistle of Paul the Apostle to the Thessalonians",
         "The First Epistle of Paul the Apostle to Timothy", "The Second Epistle of Paul the Apostle to Timothy",
         "The Epistle of Paul the Apostle to Titus", "The Epistle of Paul the Apostle to Philemon",
         "The Epistle of Paul the Apostle to the Hebrews", "The General Epistle of James",
         "The First Epistle General of Peter", "The Second General Epistle of Peter",
         "The First Epistle General of John", "The Second Epistle General of John",
         "The Third Epistle General of John", "The General Epistle of Jude", "The Revelation of Saint John the Divine"]
APOCRYPHA = ["The First Book of Esdras", "The Second Book of Esdras", "The Book of Tobit", "The Book of Judith",
             "The Greek Additions to Esther", "The Book of Wisdom", "The Book of Sirach (or Ecclesiasticus)",
             "The Book of Baruch", "The Epistle [or Letter] of Jeremiah [Jeremy]",
             "The Song of the Three Holy Children",
             "The Book of Susanna [in Daniel]", "The History of the Destruction of", "The Prayer of Manasses",
             "The First Book of the Maccabees", "The Second Book of the Maccabees"]
FILES = {"pg10.txt": OT_NT, "pg124.txt": APOCRYPHA}

# abbreviations.yaml book id -> its title, or {number: title} for a book that takes a number
_SIMPLE = dict(zip(
    ["genesis", "exodus", "leviticus", "numbers", "deuteronomy", "joshua", "judges", "ruth"], OT_NT[:8], strict=True))
_SIMPLE |= dict(zip(
    ["nehemiah", "esther", "job", "psalms", "proverbs", "ecclesiastes", "song", "isaiah", "jeremiah", "lamentations",
     "ezekiel", "daniel", "hosea", "joel", "amos"], OT_NT[15:30], strict=True))
_SIMPLE |= dict(zip(["jonah", "micah", "nahum", "habakkuk", "zephaniah", "haggai", "zechariah", "malachi", "matthew",
                     "mark", "luke"], OT_NT[31:42], strict=True))
_SIMPLE |= {"acts": OT_NT[43], "romans": OT_NT[44], "galatians": OT_NT[47], "ephesians": OT_NT[48],
            "philippians": OT_NT[49], "colossians": OT_NT[50], "titus": OT_NT[55], "hebrews": OT_NT[57],
            "james": OT_NT[58], "jude": OT_NT[64], "revelation": OT_NT[65], "tobit": APOCRYPHA[2],
            "judith": APOCRYPHA[3], "wisdom": APOCRYPHA[5], "ecclesiasticus": APOCRYPHA[6], "baruch": APOCRYPHA[7]}
TITLES: dict[str, str | dict[int, str]] = _SIMPLE | {
    "ezra": {0: "Ezra", 1: APOCRYPHA[0], 2: APOCRYPHA[1]},  # "Esdr." alone is Ezra; numbered, the Apocrypha's Esdras
    "john": {0: OT_NT[42], 1: OT_NT[61], 2: OT_NT[62], 3: OT_NT[63]},  # the Gospel; numbered, the Epistles
    "samuel": {1: OT_NT[8], 2: OT_NT[9]}, "kings": {1: OT_NT[10], 2: OT_NT[11]},
    "chronicles": {1: OT_NT[12], 2: OT_NT[13]}, "corinthians": {1: OT_NT[45], 2: OT_NT[46]},
    "thessalonians": {1: OT_NT[51], 2: OT_NT[52]}, "timothy": {1: OT_NT[53], 2: OT_NT[54]},
    "peter": {1: OT_NT[59], 2: OT_NT[60]}, "maccabees": {1: APOCRYPHA[13], 2: APOCRYPHA[14]}}
VERSE = re.compile(r"(?:(?<=\s)|^)(\d+):(\d+)\s")  # a marker may end its line ("… surely die: 3:5⏎For God …")


def check_lock() -> None:
    for line in LOCK.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            digest, name = line.split(maxsplit=1)
            f = paths.DATA / "source" / name.lstrip("*")
            if not f.exists():
                raise SystemExit(f"{f} missing: the KJV files are pinned in {LOCK}")
            if hashlib.sha256(f.read_bytes()).hexdigest() != digest:
                raise SystemExit(f"{f} does not match its hash in {LOCK}")


def _books(text: str, titles: list[str]) -> dict[str, str]:
    lines = text.replace("\r", "").split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith("*** START"))
    end = next(i for i, ln in enumerate(lines) if ln.startswith("*** END"))
    found, at = [], start
    for t in titles:
        k = at + 1
        while True:
            k = next((i for i in range(k, end) if lines[i].strip() == t), None)
            if k is None:
                raise SystemExit(f"KJV: book title {t!r} not found")
            # the first title must follow the contents list; every later one, the text of the book before it (more
            # than a subtitle: the Song of the Three Children numbers its verses without chapters)
            between = "".join(lines[at + 1:k]).strip()
            if (len(between) > 300 if found else k > start + len(titles) + 4):
                break
            k += 1
        found.append(k)
        at = k
    return {t: "\n".join(lines[a + 1:b]) for t, a, b in zip(titles, found, found[1:] + [end], strict=True)}


@cache
def books() -> dict[str, dict[tuple[int, int], str]]:
    """Title -> {(chapter, verse): text}."""
    check_lock()
    out = {}
    for name, titles in FILES.items():
        for title, text in _books((DIR / name).read_text(encoding="utf-8"), titles).items():
            parts = VERSE.split(text)
            out[title] = {(int(c), int(v)): " ".join(t.split()) for c, v, t in zip(parts[1::3], parts[2::3],
                                                                                   parts[3::3], strict=True)}
    return out


def title(book: str, n: int | None) -> str | None:
    t = TITLES.get(book)
    return t.get(n or 0) if isinstance(t, dict) else (t if not n else None)


def verses(book: str, n: int | None, ref: dict | None) -> list[tuple[int, str]] | None:
    """The KJV text of a reference's verses, [(verse, text)], or None: no verses given, a book that needs a number
    without one, or a verse the KJV does not have there."""
    if not ref or not ref.get("verses") or not (t := title(book, n)):
        return None
    vs = books()[t]
    out = [(v, vs.get((ref["chapter"], v))) for v in ref["verses"]]
    return out if all(text for _, text in out) else None
