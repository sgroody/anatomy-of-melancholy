"""The census rulings change markup only: wrapping a stretch as a passage, narrowing a passage (D13)."""

from lxml import etree

from burton.ingest import census_apply as ca
from burton.layers import census
from burton.tei import T

NS = 'xmlns="http://www.tei-c.org/ns/1.0" xmlns:ed="https://burton-edition.local/ns/gowland"'


def block(xml: str):
    return etree.fromstring(f"<p {NS}>{xml}</p>")


def text(b) -> str:
    return census.block_text(b)[0]


def test_wrap_inside_an_italic_splits_it_and_keeps_the_text():
    b = block("As he saith, <hi rend=\"i\">quod ait ille, and so on</hi> today.")
    before = text(b)
    s = ca._raw_text(b).index("quod")
    ca.wrap(b, s, s + len("quod ait ille"), "la")
    assert text(b) == before
    f = b.find(T("foreign"))
    assert "".join(f.itertext()) == "quod ait ille" and f.get("ana") == "foreign" and f.get("resp") == "#model"
    assert len(b.findall(T("hi"))) == 1 and len(f.findall(T("hi"))) == 1  # the italic split in two, one inside


def test_wrap_skips_gowland_matter_in_offsets():
    b = block("Sustine &amp; abstine <ed:trans>[bear and forbear]</ed:trans>. Next.")
    raw = ca._raw_text(b)
    assert "bear" not in raw
    s = raw.index("Sustine")
    ca.wrap(b, s, s + len("Sustine & abstine"), "la")
    assert "".join(b.find(T("foreign")).itertext()) == "Sustine & abstine"


def test_narrowing_a_passage_leaves_the_rest_foreign():
    b = block('<foreign ana="foreign" lang-tmp="la">Hor. lib. 4 od. carpe diem</foreign> said he.')
    raw = ca._raw_text(b)
    (f, f0, f1), = ca.passages(b)
    ca.unwrap(f)
    s = raw.index("carpe")
    ca.wrap(b, s, f1, "la")
    assert ["".join(x.itertext()) for x in b.iter(T("foreign"))] == ["carpe diem"]
    assert text(b) == "Hor. lib. 4 od. carpe diem said he."


def test_a_passage_is_never_split():
    b = block('<foreign ana="foreign" lang-tmp="la">alpha beta gamma</foreign> delta')
    s = ca._raw_text(b).index("beta")
    try:
        ca.wrap(b, s, len(ca._raw_text(b)), "la")
    except ca.NotPlaced:
        pass
    else:
        raise AssertionError("wrapped across a passage")
