"""The KJV reader (burton/site/kjv.py) and the in-line citation marks (stage 6)."""

import pytest

from burton.site import kjv
from burton.site.render import _visible, mark_inline_cites

needs_kjv = pytest.mark.skipif(not (kjv.DIR / "pg10.txt").exists(), reason="data/source/kjv not present")


@needs_kjv
def test_every_verse_of_the_protestant_canon_is_read():
    b = kjv.books()
    assert sum(len(b[t]) for t in kjv.OT_NT) == 31102
    assert len(b["The First Book of Samuel"]) == 810  # its subtitle names "The First Book of the Kings"


@needs_kjv
def test_a_verse_marker_at_the_end_of_a_line():
    assert kjv.verses("genesis", None, {"chapter": 3, "verses": [5]})[0][1].startswith("For God doth know")


@needs_kjv
def test_numbered_books_and_the_apocrypha():
    assert "Ashtoreth" in kjv.verses("kings", 1, {"chapter": 11, "verses": [5]})[0][1]
    assert kjv.verses("ezra", 1, {"chapter": 3, "verses": [10]})[0][1] == "The first wrote, Wine is the strongest."
    assert kjv.verses("ecclesiasticus", None, {"chapter": 1, "verses": [1]})[0][1].startswith("All wisdom")
    assert kjv.verses("samuel", None, {"chapter": 1, "verses": [1]}) is None  # which Samuel is not guessed
    assert kjv.verses("psalms", None, {"chapter": 126, "verses": [7]}) is None  # no such verse: nothing shown
    assert kjv.verses("psalms", None, {"chapter": 94, "verses": []}) is None  # a chapter alone: nothing shown


def _rec(exact, prefix, suffix, author, display, **kw):
    return {"selector": {"in": "x-p1", "exact": exact, "prefix": prefix, "suffix": suffix}, "raw": exact,
            "author": author, "display": display, **kw}


def test_the_name_stays_and_the_reference_goes_to_the_margin():
    page = "<p>and hot, as Avicenna lib. 3 Fen 1 cap. 18 holds, it is a cause</p>"
    rec = _rec("Avicenna lib. 3 Fen 1 cap. 18", "and hot, as ", " holds, it is a cause", "avicenna",
               "Avicenna, book 3, fen 1, chapter 18")
    counts = {}
    out, cards = mark_inline_cites(page, {"x-p1-ic12": rec}, counts)
    shown = _visible(out, ("cx-b", "mref"))[0]
    assert shown == "and hot, as Avicenna§ holds, it is a cause"
    assert _visible(out, ("ic-m",))[0] == "and hot, as Avicenna lib. 3 Fen 1 cap. 18 holds, it is a cause"
    assert counts["inline_cites"] == 1 and len(cards) == 1 and "book 3" in cards[0]


def test_a_bible_reference_leaves_only_the_mark_and_no_doubled_comma():
    page = "<p>’Tis all for your sins, Hag. 1. 9, 10, God is angry</p>"
    rec = _rec("Hag. 1. 9, 10", "’Tis all for your sins, ", ", God is angry", "bible", "Haggai 1:9–10",
               work="bible.haggai", ref={"chapter": 1, "verses": [9, 10]})
    out, cards = mark_inline_cites(page, {"x-p1-ic25": rec}, {})
    assert _visible(out, ("cx-b", "mref"))[0] == "’Tis all for your sins,§ God is angry"
    if (kjv.DIR / "pg10.txt").exists():
        assert "Ye looked for much" in cards[0] and "King James Bible" in cards[0]


def test_a_kept_stop_takes_the_comma_before_a_bible_reference():
    page = "<p>Amos, the 1st, Jer. 7. God is angry</p>"
    rec = _rec("Jer. 7.", "Amos, the 1st, ", " God is angry", "bible", "Jeremiah 7", work="bible.jeremiah",
               ref={"chapter": 7, "verses": []})
    out, _ = mark_inline_cites(page, {"x-p1-ic16": rec}, {})
    assert _visible(out, ("cx-b", "mref"))[0] == "Amos, the 1st§. God is angry"


def test_burtons_stop_stays_where_a_sentence_follows():
    page = "<p>as Laurentius cap. 20 lib. 1. Similar, or Homogeneal</p>"
    rec = _rec("Laurentius cap. 20 lib. 1.", "as ", " Similar, or Homogeneal", "laurentius", "André du Laurens")
    out, _ = mark_inline_cites(page, {"x-p1-ic3": rec}, {})
    assert _visible(out, ("cx-b", "mref"))[0] == "as Laurentius§. Similar, or Homogeneal"
