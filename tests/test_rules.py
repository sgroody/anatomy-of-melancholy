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
