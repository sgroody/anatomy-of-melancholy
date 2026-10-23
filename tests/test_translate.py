"""Translation validator (SPEC §6.5) and layer records: no model calls."""

from lxml import etree

from burton.tei import NSMAP, TEI_NS
from burton.textview import public_text
from burton.translate import validate

ITEM = {
    "id": "9.9.9.9-f1", "lang": "la", "kind": "phrase", "location": "text",
    "text": "Ubi tu Gaius, ego semper Gaia",
    "paragraph": "as the Bride saluted the Bridegroom, ⟦Ubi tu Gaius, ego semper Gaia⟧, "
                 "be thou still Gaius, I’ll be Gaia.",
    "sidenotes": ["Plutarch. cap. 30 Rom. hist."], "before": "", "after": "",
}
BATCH = [{"packet_item": ITEM, "text_sha1": "x", "bracket_follows": False, "unit": "9.9.9.9"}]
GLOSS = {"version": 2, "terms": [{"latin": ["ß"], "render": ["half", "½"]}]}


def entry(**kw) -> dict:
    e = {"id": "9.9.9.9-f1", "translation": "Where you are Gaius, I am always Gaia", "literal": None,
         "confidence": "high", "flags": [], "note": None, "glosses": [],
         "self_translation": {"status": "full", "burton_quote": "be thou still Gaius, I’ll be Gaia"},
         "source": {"status": "burton-cites", "author": "Plutarch", "work": None, "locus": None,
                    "basis": 'sidenote "Plutarch. cap. 30 Rom. hist."'}}
    e.update(kw)
    return e


def errors(e: dict, batch=BATCH, gloss=GLOSS) -> list[str]:
    return [x["msg"] for x in validate.check({"passages": [e]}, batch, gloss) if x["severity"] != "warning"]


def test_clean_entry_passes():
    assert errors(entry()) == []


def test_explanation_in_parentheses_is_retried():
    msgs = errors(entry(translation="Where you are Gaius (the husband), I am always Gaia"))
    assert any("parenthesis" in m for m in msgs)


def test_parentheses_from_the_source_are_allowed():
    item = dict(ITEM, text="Ego (inquit) utor", paragraph="⟦Ego (inquit) utor⟧")
    e = entry(translation="I (says he) use it", self_translation={"status": "none", "burton_quote": None},
              source={"status": "unidentified", "author": None, "work": None, "locus": None, "basis": None})
    assert errors(e, [dict(BATCH[0], packet_item=item)]) == []


def test_burton_cites_needs_a_quoted_basis_found_in_context():
    bad = entry(source={"status": "burton-cites", "author": "Plutarch", "work": None, "locus": None,
                        "basis": "Burton names Plutarch"})
    assert any("burton-cites" in m for m in errors(bad))
    invented = entry(source={"status": "burton-cites", "author": "Livy", "work": None, "locus": None,
                             "basis": 'sidenote "Liv. lib. 1."'})
    assert any("burton-cites" in m for m in errors(invented))
    rec = validate.to_record(None, invented, BATCH[0], "m", "tr-v2", ["m"], [])
    assert rec["source"]["status"] == "unidentified" and rec["source"]["downgraded_from"] == "burton-cites"


def test_in_text_attribution_counts_as_burton_cites():
    item = dict(ITEM, paragraph="⟦caedem scripturarum faciunt⟧, saith Tertullian, they make a slaughter", sidenotes=[])
    e = entry(self_translation={"status": "none", "burton_quote": None},
              source={"status": "burton-cites", "author": "Tertullian", "work": None, "locus": None,
                      "basis": 'text "saith Tertullian"'})
    assert errors(e, [dict(BATCH[0], packet_item=item)]) == []


def test_quote_inside_the_passage_is_not_a_self_translation():
    e = entry(self_translation={"status": "full", "burton_quote": "ego semper Gaia"})
    assert any("burton_quote" in m for m in errors(e))
    rec = validate.to_record(None, e, BATCH[0], "m", "tr-v2", ["m"], [])
    assert rec["self_translation"]["status"] == "undetermined"


def test_glossary_matches_symbols():
    item = dict(ITEM, text="℞ Alkermes ℥ ß", paragraph="⟦℞ Alkermes ℥ ß⟧")
    e = entry(translation="Take confection of Alkermes, an ounce", self_translation={"status": "none",
              "burton_quote": None}, source={"status": "unidentified", "author": None, "work": None,
                                             "locus": None, "basis": None})
    warns = [x["msg"] for x in validate.check({"passages": [e]}, [dict(BATCH[0], packet_item=item)], GLOSS)]
    assert any("glossary: ß" in m for m in warns)


def test_gloss_only_items():
    item = {"id": "9.9.9.9-lg1", "lang": "enm", "kind": "gloss-only", "location": "text",
            "text": "For all to sicker, as cold engendreth hail", "paragraph": "", "sidenotes": []}
    b = [{"packet_item": item, "text_sha1": "x", "bracket_follows": False, "unit": "9.9.9.9"}]
    good = entry(id="9.9.9.9-lg1", translation="", glosses=[{"word": "to sicker", "sense": "for certain"}],
                 self_translation={"status": "none", "burton_quote": None})
    assert errors(good, b) == []
    assert errors(dict(good, translation="For certain, as cold breeds hail"), b)
    assert errors(dict(good, glosses=[{"word": "sickerly", "sense": "certainly"}]), b)
    rec = validate.to_gloss_record(None, good, b[0], "m", "tr-v2", ["m"], [])
    sel = rec["glosses"][0]["items"][0]["selector"]
    assert item["text"].count(sel["prefix"] + sel["exact"] + sel["suffix"]) == 1


def test_two_models_keep_their_own_verdicts_and_the_primary_leads():
    opus = validate.to_record(None, entry(), BATCH[0], validate.PRIMARY_MODEL, "tr-v2", [], [])
    other = entry(self_translation={"status": "none", "burton_quote": None},
                  source={"status": "unidentified", "author": None, "work": None, "locus": None, "basis": None})
    both = validate.to_record(opus, other, BATCH[0], "claude-sonnet-5-5", "tr-v2", [], [])
    assert [t["model"] for t in both["translations"]] == [validate.PRIMARY_MODEL, "claude-sonnet-5-5"]
    assert both["self_translation"]["status"] == "full" and both["source"]["status"] == "burton-cites"
    assert both["translations"][1]["self_translation"]["status"] == "none"
    assert validate.primary_machine(both)["model"] == validate.PRIMARY_MODEL


def test_public_text_reads_a_correction_as_corr():
    e = etree.fromstring(f'<p xmlns="{TEI_NS}" xmlns:ed="{NSMAP["ed"]}"><choice><sic>Mανία</sic>'
                         f'<corr resp="#editor">Μανία</corr></choice> γὰρ</p>')
    assert public_text(e) == "Μανία γὰρ"
