"""M5 preparation: Chaucer tagging, verse-group language rules, inline manual decisions, runner bookkeeping."""

from collections import Counter

from lxml import etree

from burton.ingest import langid, manual
from burton.tei import NSMAP, TEI_NS, XML_LANG, T
from burton.translate import runner


def div_of(blocks: str):
    return etree.fromstring(f'<div xmlns="{TEI_NS}" xmlns:ed="{NSMAP["ed"]}">{blocks}</div>')


def text(e) -> str:
    return "".join(e.itertext())


def test_chaucer_is_tagged_enm_but_is_not_a_passage():
    d = div_of('<quote type="block"><lg><l><hi rend="lucida">For Gold in Physic is a cordial,</hi></l>'
               '<l><hi rend="lucida">Therefore he loved Gold in special.</hi></l></lg></quote>')
    before = text(d)
    stats = Counter()
    langid.tag_chaucer(d, stats)
    tags = list(d.iter(T("foreign")))
    assert stats["script:enm"] == 2 and all(f.get(XML_LANG) == "enm" for f in tags)
    assert all(f.get("ana") is None for f in tags)  # glossed, never translated
    assert text(d) == before


def test_english_lines_after_latin_in_one_group_are_split_off():
    d = div_of('<quote type="block"><lg><l><hi rend="i">Sed revocare gradum, superasque evadere ad auras;</hi></l>'
               '<l><hi rend="i">Hic labor, hoc opus est</hi>.</l>'
               '<l>It is an easy passage down to hell,</l>'
               '<l>But to come back, once there, you cannot well.</l></lg></quote>')
    before = text(d)
    stats = Counter()
    langid.split_english_tail(d, stats)
    lgs = list(d.iter(T("lg")))
    assert stats["lg:english-tail-split"] == 1 and len(lgs) == 2
    assert lgs[1].get("type") == "translation-block" and len(lgs[1]) == 2
    assert text(d) == before
    langid.tag_verse_latin(d, [], "t")
    assert lgs[0].get("ana") == "foreign" and lgs[1].get("ana") is None


def test_english_verse_with_italic_latin_names_is_not_latin():
    d = div_of('<quote type="block"><lg><l><hi rend="i">Non me carminibus vincet nec Thraceus Orpheus</hi></l></lg>'
               '<lg type="translation-block"><l>Wanton <hi rend="i">Propertius</hi>, '
               'and witty <hi rend="i">Gallus</hi>,</l>'
               '<l>Subtle <hi rend="i">Tibullus</hi>, and learned <hi rend="i">Catullus</hi>,</l></lg>'
               '<lg type="translation-block"><l>Nor Orpheus shall outdo me in my song.</l></lg></quote>')
    langid.tag_verse_latin(d, [], "t")
    lgs = list(d.iter(T("lg")))
    assert lgs[0].get("ana") == "foreign"
    assert lgs[1].get("ana") is None  # its italics are names; the whole group is English


def test_inline_decisions(monkeypatch):
    monkeypatch.setattr(manual, "blocks", lambda: {"inline": [
        {"unit": "t", "in": "a1", "phrase": "à la mort", "lang": "fr"},
        {"unit": "t", "in": "a2", "phrase": "a bella Donna", "lang": "it"},
        {"unit": "t", "in": "a3", "whole": True, "lang": "la"},
        {"unit": "t", "in": "a4", "verse": True, "lang": "it"},
    ]})
    d = div_of('<p src="x#a1">if idle, or alone, à la mort, or carried away</p>'
               '<p src="x#a2"><hi rend="i">a bella Donna</hi>, quae salivam moveat</p>'
               '<p src="x#a3">Huc faciunt <hi rend="i">medicamenta</hi> Venerem sopientia.</p>'
               '<quote type="block"><lg><l src="x#a4"><hi rend="i">Chi non tocca parentado,</hi></l></lg></quote>')
    before = text(d)
    stats = manual.apply_inline(d, "t")
    assert stats["language-inline"] == 4 and text(d) == before
    fr, it, la = [f for f in d.iter(T("foreign"))]
    assert (fr.get(XML_LANG), text(fr)) == ("fr", "à la mort")
    assert it.get(XML_LANG) == "it" and it[0].tag == T("hi")  # the italic run is wrapped, not nested inside
    assert la.getparent().get("src") == "x#a3" and text(la) == text(la.getparent())
    assert d.find(f".//{T('lg')}").get(XML_LANG) == "it"
    # the rules leave decided text alone
    langid.tag_latin(d, [], "t")
    assert sum(1 for f in d.iter(T("foreign")) if f.get("ana") == "foreign") == 3


def test_a_language_change_makes_a_record_stale():
    rec = {"text_sha1": "s", "lang": "la", "translations": [
        {"by": "machine", "model": "m", "prompt": runner.PROMPT}]}
    assert runner.is_current(rec, "s", "m", "la")
    assert not runner.is_current(rec, "s", "m", "it")


def test_orphan_records_are_retired_not_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.paths, "LAYERS", tmp_path)
    runner.write_layer("u", {"u-f1": {"text": "a"}, "u-f2": {"text": "b"}})
    assert runner.retire_orphans("u", {"u-f1"}) == ["u-f2"]
    assert list(runner.read_layer("u")) == ["u-f1"]
    old = runner.read_layer("u", "retired/translations")
    assert old["u-f2"]["text"] == "b" and old["u-f2"]["retired"]["reason"]


def test_burton_span_selector_grows_until_unique_and_knows_its_view():
    from burton.translate import validate

    item = {"paragraph": "a priest and a physician at once, and a man"}
    main = "He was at once a priest and a physician at once, and a man at once."
    sel = validate.span_selector(item, "physician at once", (main, main))
    assert sel["prefix"] == "" and "view" not in sel  # already unique
    sel = validate.span_selector(item, "at once", (main, main))
    assert main.count(sel["prefix"] + "at once" + sel["suffix"]) == 1 and "physician ".endswith(sel["prefix"])
    # Burton's rendering stands in a sidenote: found only in the text with notes
    note_item = {"paragraph": "bank of charity, saith he"}
    sel = validate.span_selector(note_item, "bank of charity", ("main text", "main text bank of charity, saith he"))
    assert sel["view"] == "with-notes"
