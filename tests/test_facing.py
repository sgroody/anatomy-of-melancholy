"""Long verse passages set facing their translation (stage 7, T12 B), and Burton's own renderings' language."""

from lxml import etree

from burton.site.render import FACING_MIN, Renderer, mark_burton_spans
from burton.tei import XML_ID, T


def _lg(n: int, xid: str = "u9.9.9.9-lg1"):
    lg = etree.Element(T("lg"))
    lg.set(XML_ID, xid)
    for k in range(n):
        etree.SubElement(lg, T("l")).text = f"line {k}"
    return lg


def _renderer(text: str) -> Renderer:
    r = Renderer("9.9.9.9", "private", {})
    r.gowland = {"9.9.9.9-lg1": text}
    return r


def test_a_translation_line_for_line_is_set_facing():
    lines = " / ".join(f"tr {k}" for k in range(FACING_MIN))
    assert _renderer(lines).facing_lines(_lg(FACING_MIN), "9.9.9.9-lg1")[0][-1] == f"tr {FACING_MIN - 1}"
    assert _renderer(lines).facing_lines(_lg(FACING_MIN + 1), "9.9.9.9-lg1") is None  # lines do not match
    short = " / ".join(["a"] * (FACING_MIN - 1))
    assert _renderer(short).facing_lines(_lg(FACING_MIN - 1), "9.9.9.9-lg1") is None  # short: a margin card


def test_gowland_running_on_from_the_passage_before():
    text = " / ".join(f"tr {k}" for k in range(16))
    r = _renderer(text)
    r.last_block = ("9.9.9.9-lg0", 4)  # four lines before, with no Gowland version of their own
    lines, v = r.facing_lines(_lg(12), "9.9.9.9-lg1")
    assert v["by"] == "gowland" and lines[0] == "tr 4" and len(lines) == 12
    r = _renderer(text)
    r.last_block = ("9.9.9.9-lg0", 5)  # the extra lines are not that passage's: no guess
    assert r.facing_lines(_lg(12), "9.9.9.9-lg1") is None


def test_burtons_rendering_carries_its_original_language():
    layer = {"x-f1": {"self_translation": {"burton_span": {"exact": "Th’ earth’s full of maladies"}}}}
    counts = {"burton_spans": 0, "burton_spans_unplaced": 0}
    out = mark_burton_spans("<p>Th’ earth’s full of maladies</p>", layer, counts, {"x-f1": "grc"})
    assert 'data-lang="grc"' in out and counts["burton_spans"] == 1
