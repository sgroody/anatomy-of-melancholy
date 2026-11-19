"""Unit tests for the rules that decide what is Gowland's, what is foreign, and what a model may claim."""

from lxml import etree

from burton.ids import Registry
from burton.ingest import gowland, langid
from burton.tei import ED, NSMAP, TEI_NS, T, el
from burton.textview import public_text
from burton.translate import validate


def tei(fragment: str):
    return etree.fromstring(
        f'<p xmlns="{TEI_NS}" xmlns:ed="{NSMAP["ed"]}">{fragment}</p>')


# ---------------------------------------------------------------- Gowland separation

def test_bracket_becomes_ed_trans_and_keeps_text():
    p = tei('<hi rend="i">Quisque suos patimur manes</hi> [Each of us suffers], we have')
    before = "".join(p.itertext())
    stats = gowland.separate(p)
    assert stats["trans"] == 1
    assert "".join(p.itertext()) == before  # nothing lost or altered
    t = p.find(ED("trans"))
    assert "".join(t.itertext()) == "[Each of us suffers]"


def test_brace_inside_bracket_is_supplied():
    p = tei("[we know, and {claim} that licence, etc.]")
    gowland.separate(p)
    t = p.find(ED("trans"))
    assert t is not None and t.find(T("supplied")).text == "{claim}"


def test_unmatched_bracket_is_counted_not_guessed():
    p = tei("an opening [bracket with no end")
    stats = gowland.separate(p)
    assert stats["trans"] == 0 and stats["trans:unmatched-open"] == 1
    assert "".join(p.itertext()) == "an opening [bracket with no end"


def div_of(blocks: str):
    return etree.fromstring(f'<div xmlns="{TEI_NS}" xmlns:ed="{NSMAP["ed"]}">{blocks}</div>')


SPANNING = ('<p><foreign>Latine dictum</foreign> [The translation begins'
            '<note type="side" n="1">His English sidenote.</note> here,</p>'
            '<quote type="block"><lg type="translation-block"><l>a verse he translated,</l></lg></quote>'
            '<p>goes on</p><p>and ends here]. Burton again.</p>')


def test_bracket_over_several_blocks_is_separated_piece_by_piece():
    div = div_of(SPANNING)
    before = "".join(div.itertext())
    stats = gowland.separate(div)
    assert "".join(div.itertext()) == before  # nothing lost or altered
    assert stats["trans"] == 1 and stats["trans:across-blocks"] == 1
    assert not any("unmatched" in k for k in stats)
    assert [t.get("part") for t in div.iter(ED("trans"), ED("verse-trans"))] == ["I", "M", "M", "F"]
    assert div.find(f".//{ED('verse-trans')}/{T('lg')}").get("type") is None  # not Burton's own verse
    assert public_text(div, notes=True) == "Latine dictum. Burton again."  # his sidenote went with it


def test_irregular_bracket_over_blocks_stays_unmatched():
    div = div_of("<p>one [opens</p><p>with <hi>a stray ] inside</hi></p><p>closes]</p>")
    stats = gowland.separate(div)
    assert stats["trans:across-blocks"] == 0 and stats["trans:unmatched-open"] >= 1
    assert div.find(f".//{ED('trans')}") is None


def test_bracketed_verse_over_two_stanzas_and_before_a_full_stop():
    from burton.ingest import convert

    q = etree.fromstring(
        f'<quote xmlns="{TEI_NS}" xmlns:ed="{NSMAP["ed"]}">'
        '<lg><l>Latina carmina</l></lg>'
        '<lg type="translation-block"><l>[Take this;</l><l>mix it].</l></lg>'
        '<lg type="translation-block"><l>[First stanza,</l></lg><lg type="translation-block"><l>second.]</l></lg>'
        '<lg type="translation-block"><l>[a] Burton [b]</l></lg></quote>')
    convert._mark_gowland_verse(q)
    wrapped = [(w.get("part"), "".join(w.itertext())) for w in q.iter(ED("verse-trans"))]
    assert wrapped == [(None, "[Take this;mix it]."), ("I", "[First stanza,"), ("F", "second.]")]
    assert q[-1].tag == T("lg")  # brackets closing mid-group are left to the inline pass


def test_v8t_fails_on_a_bracket_left_in_public_text(tmp_path, monkeypatch):
    from burton import paths
    from burton.verify import checks

    def unit(name: str, body: str) -> None:
        (tmp_path / f"{name}.xml").write_text(
            f'<TEI xmlns="{TEI_NS}" xmlns:ed="{NSMAP["ed"]}"><text><body><div n="{name}">{body}</div>'
            '</body></text></TEI>', encoding="utf-8")

    monkeypatch.setattr(paths, "TEXT", tmp_path)
    unit("good", "<p>Latina <ed:trans>[English]</ed:trans>.</p>")
    unit("bad", "<p>Latina [English</p><p>more]</p><p>a <hi>[stray</hi> b]</p>")
    assert checks.v8_public_text(["good"]).ok
    r = checks.v8_public_text(["good", "bad"])
    assert not r.ok and r.counts["brackets_left"] == 4 and r.counts["trans"] == 1


def test_public_text_never_contains_gowland():
    p = tei('<hi rend="i">Lethales</hi> <ed:trans>[fatal]</ed:trans>, <supplied resp="#gowland">{is}</supplied> x')
    assert "fatal" not in public_text(p) and "{is}" not in public_text(p)


# ---------------------------------------------------------------- language rules

def test_classify():
    assert langid.classify("morborum infinita multitudo", False)[0] == "la"
    assert langid.classify("Quisque suos patimur manes", True)[0] == "la"
    assert langid.classify("could not remember that ever he was sick", False)[0] == "en"
    assert langid.classify("Hercules de Saxonia", False)[0] == "name"
    assert langid.classify("Fern. Path. lib. 1 cap. 1", False)[0] == "citation"
    assert langid.classify("Oper. & dies", False, in_note=True)[0] == "citation"
    # a lone English word: English by the book lexicon if it is built, otherwise undetermined, never Latin
    assert langid.classify("parts", False)[0] in ("en", "undetermined")
    assert langid.classify("&c", False)[0] != "la"


def test_etc_is_not_the_locator_c():
    assert not langid.CITATION.search("trahunt, &c., id omne misellis Indis")
    assert langid.CITATION.search("lib. 3 c. 4")


def test_authors_and_abbreviated_titles_are_citations():
    run = "Lessius, Morneus, Grotius de verit. Relig. Christianae, Savonarola de verit. fidei Christianae"
    assert langid.classify(run, False)[0] == "citation"
    assert langid.classify("&c. Cardan de subt", False, stop=True)[0] == "citation"
    # a bracket means Gowland translated it: then it is a passage, whatever it looks like
    assert langid.classify("Cardan de subt", True, stop=True)[0] == "la"


def test_de_before_a_capital_is_a_name_particle():
    assert langid.classify("Herc. de Saxonia, stillicidia", False)[0] != "la"


def test_english_run_is_split_at_a_sentence_break():
    p = tei('<hi rend="i">he forsook the City, and all night</hi>. <hi rend="i">Quae quidem</hi> (saith he)')
    langid.tag_latin(p, [], "t")
    assert [public_text(f) for f in p.iter(T("foreign"))] == ["Quae quidem"]


def test_citation_fragments_are_shed_before_a_bracket_after_a_stop():
    p = tei('<hi rend="i">Galen</hi>. <hi rend="i">lib</hi>. <hi rend="i">3 cap</hi>. '
            '<hi rend="i">Animus maerens inde malum trahit</hi>. <ed:trans>[x]</ed:trans>')
    langid.tag_latin(p, [], "t")
    assert [public_text(f) for f in p.iter(T("foreign"))] == ["Animus maerens inde malum trahit"]


def test_a_string_of_abbreviations_before_a_bracket_is_not_a_passage():
    p = tei('<hi rend="i">Lat</hi>. <hi rend="i">10</hi>. <hi rend="i">Gr</hi>. <hi rend="i">Aust</hi>. '
            '<ed:trans>[At latitude 10° south.]</ed:trans>')
    langid.tag_latin(p, [], "t")
    assert p.find(T("foreign")) is None


def test_comma_list_is_split_into_items():
    p = tei('<hi rend="i">Savonarola</hi>, <hi rend="i">Capivaccius</hi>, <hi rend="i">Hercules de Saxonia</hi>')
    decisions = []
    langid.tag_latin(p, decisions, "t")
    assert [d["verdict"] for d in decisions] == ["name", "name", "name"]
    assert p.find(T("foreign")) is None


def test_a_latin_title_after_a_title_noun_is_a_citation():
    p = tei('<hi rend="i">Prosper Calanius</hi> in his book <hi rend="i">de atra bile</hi>, will have them')
    langid.tag_latin(p, [], "t")
    assert p.find(T("foreign")) is None
    # Gowland translates titles too: after a title noun the bracket does not make it a passage
    p = tei('in a consultation of his <hi rend="i">pro hypocondriaco</hi> <ed:trans>[for a hypochondriac]</ed:trans>')
    langid.tag_latin(p, [], "t")
    langid.tag_roman_before_brackets(p, [], "t")  # nor does the bracket pass take it back
    langid.finalize_lang(p)
    assert p.find(T("foreign")) is None and p.find(T("hi")).get("lang-title") is None
    # quoted Latin opening with "de" elsewhere is still a passage
    p = tei('they say <hi rend="i">de inanibus semper conqueruntur, &amp; timent</hi>')
    langid.tag_latin(p, [], "t")
    assert p.find(T("foreign")) is not None


def test_a_title_after_an_abbreviation_in_a_note_is_a_citation():
    n = tei('<note type="side"><hi rend="i">Origo ejus a Coelo petenda est</hi> <ed:trans>[x]</ed:trans>. '
            '<hi rend="i">Tr</hi>. <hi rend="i">de morbis amentium</hi>.</note>')
    langid.tag_latin(n, [], "t")
    assert [public_text(f) for f in n.iter(T("foreign"))] == ["Origo ejus a Coelo petenda est"]


def test_latin_with_only_latin_ambiguous_english_words():
    assert langid.classify("Deos suos patrio more venerantur", False)[0] == "la"


def test_superscript_ending_joins_its_run_and_is_never_cut():
    p = tei('<hi rend="i">Si dominus 7</hi><hi rend="sup-i">mae</hi> <hi rend="i">in 7</hi><hi rend="sup-i">ma</hi> '
            '<hi rend="i">vel secunda nobilem decernit uxorem</hi>. <hi rend="i">Si Venus in 12</hi>'
            '<hi rend="sup-i">ma</hi>, <hi rend="i">&amp;c</hi>. <ed:trans>[x]</ed:trans>')
    langid.tag_latin(p, [], "t")
    fs = [public_text(f) for f in p.iter(T("foreign"))]
    assert len(fs) == 1 and fs[0].startswith("Si dominus 7mae") and "12ma" in fs[0]


def test_a_latin_clause_inside_an_english_italic_run():
    p = tei('<hi rend="i">I am undone, I cannot endure these love pangs, what shall I do? '
            'Vos O dii Averrunci, solvite me his curis</hi>, O ye Gods')
    langid.tag_latin(p, [], "t")
    assert [public_text(f) for f in p.iter(T("foreign"))] == ["Vos O dii Averrunci, solvite me his curis"]
    # inside a run that ends in a reference ("…folly. David Crusius Theat. … lib. 2 cap. 6")
    p = tei('<hi rend="i">Capivaccius</hi>, <hi rend="i">si cerebrum sit calidius, if the brain be hot, the animal '
            'spirits will be hot: if cold, folly</hi>. <hi rend="i">David Crusius Theat</hi>. <hi rend="i">lib</hi>. '
            '<hi rend="i">2 cap</hi>. <hi rend="i">6 de atra bile</hi>, grants')
    langid.tag_latin(p, [], "t")
    assert [public_text(f) for f in p.iter(T("foreign"))] == ["si cerebrum sit calidius"]
    assert "Capivaccius, si cerebrum sit calidius, if the brain" in public_text(p)  # text unchanged
    # a piece cut out of a reference run is Latin only on strong evidence
    p = tei('<hi rend="i">as they say of that country, and so do all writers</hi>. <hi rend="i">Vide Isaacum Pontanum '
            'descript</hi>. <hi rend="i">Amstel</hi>. <hi rend="i">lib</hi>. <hi rend="i">2 cap</hi>. '
            '<hi rend="i">3</hi>')
    langid.tag_latin(p, [], "t")
    assert p.find(f".//{T('foreign')}") is None


def test_greek_run_includes_elision_marks():
    p = tei("Νοῦσοι δʼ ἀνθρώποισιν ἐφ̓ ἡμέρῃ, and English")
    langid._wrap_script_runs(p, __import__("collections").Counter())
    f = p.find(T("foreign"))
    assert f.text == "Νοῦσοι δʼ ἀνθρώποισιν ἐφ̓ ἡμέρῃ"


# ---------------------------------------------------------------- ids

def test_registry_is_stable_and_never_reuses(tmp_path):
    reg = Registry(tmp_path / "r.tsv")
    a = reg.assign("1.1.1.2", "p", "x#1")
    b = reg.assign("1.1.1.2", "p", "x#2")
    reg.save()
    reg2 = Registry(tmp_path / "r.tsv")
    assert reg2.assign("1.1.1.2", "p", "x#2") == b  # same locator, same id
    assert reg2.finish_unit("1.1.1.2") == 1  # x#1 not seen again: retired
    c = reg2.assign("1.1.1.2", "p", "x#3")
    assert c not in (a, b)  # retired numbers are never reused


# ---------------------------------------------------------------- what a model may claim

ITEM = {"id": "u-f1", "lang": "la", "kind": "phrase", "text": "morborum infinita multitudo", "location": "text",
        "sidenotes": [],
        "paragraph": "elsewhere he saith, ⟦morborum infinita multitudo⟧, their number is infinite.",
        "after": "", "before": ""}
BATCH = [{"packet_item": ITEM, "text_sha1": "x", "bracket_follows": False, "unit": "u"}]


def entry(**kw):
    e = {"id": "u-f1", "translation": "an infinite multitude of diseases", "literal": None, "confidence": "high",
         "flags": [], "note": None, "self_translation": {"status": "none", "burton_quote": None},
         "source": {"status": "unidentified", "author": None, "work": None, "locus": None, "basis": None}}
    e.update(kw)
    return e


def test_self_translation_quote_must_be_burtons_words():
    assert validate.quote_ok(ITEM, "their number is infinite")
    assert not validate.quote_ok(ITEM, "the number is infinite")  # not copied exactly
    assert not validate.quote_ok(ITEM, "morborum infinita")  # that is the passage itself


def test_invented_quote_is_downgraded_not_accepted():
    bad = entry(self_translation={"status": "full", "burton_quote": "an invented rendering"})
    errs = validate.check({"passages": [bad]}, BATCH, {"terms": []})
    assert any(e["severity"] == "retry" for e in errs)
    rec = validate.to_record(None, bad, BATCH[0], "m", "p", ["m"], errs)
    assert rec["self_translation"]["status"] == "undetermined"


def test_probable_source_without_basis_becomes_unidentified():
    bad = entry(source={"status": "probable", "author": "Pliny", "work": "Natural History", "locus": None,
                        "basis": None})
    rec = validate.to_record(None, bad, BATCH[0], "m", "p", ["m"], [])
    assert rec["source"]["status"] == "unidentified"
    assert rec["source"]["downgraded_from"] == "probable"
    assert rec["source"]["verified"] is False


def test_machine_record_is_labelled():
    rec = validate.to_record(None, entry(), BATCH[0], "claude-opus-5-5", "tr-v1", ["claude-opus-5-5"], [])
    m = rec["translations"][0]
    assert m["by"] == "machine" and m["model"] == "claude-opus-5-5" and m["prompt"] == "tr-v1" and m["date"]


def test_el_helper_uses_tei_namespace():
    assert el("p").tag == T("p")
