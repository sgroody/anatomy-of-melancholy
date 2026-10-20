"""Self-translation signals (SPEC §6.2): rules only, selectors unique, Gowland's text never in the layer."""

import json
from collections import Counter

from lxml import etree

from burton import paths
from burton.layers import selftrans
from burton.tei import NSMAP, TEI_NS
from burton.verify import layers


def unit(body: str):
    return etree.fromstring(
        f'<TEI xmlns="{TEI_NS}" xmlns:ed="{NSMAP["ed"]}"><text><body>'
        f'<div type="subsection" n="9.9.9.9" xml:id="u9.9.9.9">{body}</div></body></text></TEI>')


def la(n: int, text: str) -> str:
    return f'<foreign ana="foreign" xml:lang="la" xml:id="u9.9.9.9-f{n}"><hi rend="i">{text}</hi></foreign>'


def records(body: str) -> dict:
    return selftrans.unit_records(unit(body), Counter())


def spans(rec: dict) -> dict[str, str]:
    return {c["position"]: c["selector"]["exact"] for c in rec["candidates"]}


# ---------------------------------------------------------------- brackets

def test_bracket_none_present_short():
    r = records(
        f'<p xml:id="u9.9.9.9-p1">{la(1, "morborum infinita multitudo")}, their number is infinite. '
        f'{la(2, "Quisque suos patimur manes")} <ed:trans for="u9.9.9.9-f2">[Each of us suffers his own]</ed:trans>, '
        f'we have all our infirmities. {la(3, "Qui quoad pueritiae ultimam memoriam recordari potest")} '
        f'<ed:trans for="u9.9.9.9-f3">[A man]</ed:trans> could not remember.</p>')
    assert r["9.9.9.9-f1"]["bracket"] == "none" and "no-gowland-bracket" in r["9.9.9.9-f1"]["signals"]
    assert r["9.9.9.9-f2"]["bracket"] == "present" and "no-gowland-bracket" not in r["9.9.9.9-f2"]["signals"]
    assert r["9.9.9.9-f3"]["bracket"] == "short" and "short-gowland-bracket" in r["9.9.9.9-f3"]["signals"]


def test_gowland_text_never_reaches_the_layer():
    r = records(f'<p xml:id="u9.9.9.9-p1">{la(1, "Lethales")} <ed:trans for="u9.9.9.9-f1">[ZZfatal]</ed:trans>, '
                f'<supplied resp="#gowland">{{ZZis}}</supplied> they kill the patient outright.</p>')
    assert "ZZ" not in json.dumps(r)
    sel = r["9.9.9.9-f1"]["candidates"][0]["selector"]
    assert not any(ch in sel[k] for k in ("prefix", "exact", "suffix") for ch in "[]{}")
    assert spans(r["9.9.9.9-f1"])["following"] == "they kill the patient outright"


# ---------------------------------------------------------------- candidate spans

def test_following_clause_with_cognates():
    r = records(f'<p xml:id="u9.9.9.9-p1">Pliny reckons up 300: elsewhere he saith, '
                f'{la(1, "morborum infinita multitudo")}, their number is infinite. Howsoever it was.</p>')
    rec = r["9.9.9.9-f1"]
    c = rec["candidates"][0]
    assert c["position"] == "following" and c["selector"]["exact"] == "their number is infinite"
    assert c["relation"] == "clause" and c["by"] == "rules" and c["cognates"] == 1
    assert "cognate-overlap" in rec["signals"]
    # the clause before is only an attribution ("elsewhere he saith"): not a candidate
    assert "preceding" not in spans(rec)


def test_attribution_is_stepped_over():
    r = records(f'<p xml:id="u9.9.9.9-p1">And so {la(1, "homo homini lupus")}, saith Plautus, one man is a wolf '
                f'to another; and so on.</p>')
    c = r["9.9.9.9-f1"]["candidates"][0]
    assert c["selector"]["exact"] == "one man is a wolf to another" and c["after_attribution"] is True


def test_next_sentence_when_the_passage_ends_one():
    r = records(f'<p xml:id="u9.9.9.9-p1">As the Poet hath it, {la(1, "Omnia vincit amor.")} '
                f'Love overcomes all things, saith he. Next.</p>')
    c = next(c for c in r["9.9.9.9-f1"]["candidates"] if c["position"] == "following")
    assert c["relation"] == "sentence" and c["selector"]["exact"] == "Love overcomes all things, saith he"


def test_gloss_cue():
    r = records(f'<p xml:id="u9.9.9.9-p1">{la(1, "Hypochondriaci")}, i.e. windy melancholy men; and '
                f'{la(2, "atra bilis")}, that is, black choler, the cause.</p>')
    assert r["9.9.9.9-f1"]["candidates"][0]["cue"] == "i.e."
    c = r["9.9.9.9-f2"]["candidates"][0]
    assert c["cue"] == "that is" and c["selector"]["exact"] == "that is, black choler, the cause"
    assert "gloss-cue" in r["9.9.9.9-f2"]["signals"]


def test_unseparated_gowland_brackets_are_never_copied():
    # a bracket ingest did not separate stays in the public view as plain text: no candidate may touch it
    r = records(f'<p xml:id="u9.9.9.9-p1">{la(1, "nunc sextum")} [ZZ for the sixth time I picked up my pen] '
                f'a kind of writing; {la(2, "pro virili")}, as well as I could, and so on.</p>')
    assert "ZZ" not in json.dumps(r) and r["9.9.9.9-f1"]["candidates"] == []
    assert spans(r["9.9.9.9-f2"])["following"] == "as well as I could, and so on"
    r = records('<quote><lg ana="foreign" xml:lang="la" xml:id="u9.9.9.9-f1"><l>Aeternitas illud verbum</l></lg>'
                '<lg type="translation-block" xml:id="u9.9.9.9-lg2"><l>[ZZ ‘Eternity’ is that word]</l></lg></quote>')
    assert r["9.9.9.9-f1"]["candidates"] == []
    assert selftrans.unseparated("a [b] c {d") == [(2, 5), (8, 10)]


def test_preceding_clause_and_locators_do_not_end_sentences():
    r = records(f'<p xml:id="u9.9.9.9-p1">See lib. 3 cap. 2. Man is a wolf to man in this age of ours, '
                f'{la(1, "homo homini lupus")}.</p>')
    assert spans(r["9.9.9.9-f1"])["preceding"] == "Man is a wolf to man in this age of ours"


def test_candidate_stops_at_the_next_passage_and_rejects_latin_or_citations():
    r = records(f'<p xml:id="u9.9.9.9-p1">{la(1, "nec tamen")} Plin. lib. 7 cap. 31; '
                f'{la(2, "virtus laudatur")}, et alget nunc et semper; {la(3, "Aegrotat")} and then '
                f'{la(4, "Fortuna")} it is.</p>')
    assert "following" not in spans(r["9.9.9.9-f1"])  # a citation
    assert "following" not in spans(r["9.9.9.9-f2"])  # untagged Latin
    assert spans(r["9.9.9.9-f3"])["following"] == "and then"  # cut where the next passage starts


def test_sidenote_latin_points_at_the_text_after_its_anchor():
    r = records(f'<p xml:id="u9.9.9.9-p1">being a very old man, <note type="side" n="1" xml:id="u9.9.9.9-n1">'
                f'{la(1, "non meminit se aegrotum decubuisse")}.</note><hi rend="i">could not remember that ever '
                f'he was sick</hi>. Paracelsus may brag.</p>')
    rec = r["9.9.9.9-f1"]
    assert rec["location"] == "sidenote" and "english-at-anchor" in rec["signals"]
    c = next(c for c in rec["candidates"] if c["position"] == "note-anchor")
    assert c["selector"]["in"] == "9.9.9.9-p1" and c["selector"]["exact"] == "could not remember that ever he was sick"


def test_burton_verse_after_verse():
    r = records('<quote><lg ana="foreign" xml:lang="la" xml:id="u9.9.9.9-f1"><l>Terris incubuit cohors.</l></lg>'
                '<ed:verse-trans for="u9.9.9.9-f1"><lg xml:id="u9.9.9.9-lg2"><l>[ZZ oppressed]</l></lg>'
                '</ed:verse-trans><lg type="translation-block" xml:id="u9.9.9.9-lg3"><l>Th’ earth’s full of '
                'maladies,</l><l>Which set upon us.</l></lg></quote>')
    rec = r["9.9.9.9-f1"]
    assert rec["location"] == "verse" and rec["bracket"] == "present"
    assert spans(rec) == {"verse-following": "Th’ earth’s full of maladies, / Which set upon us."}
    assert rec["candidates"][0]["selector"]["in"] == "9.9.9.9-lg3"


def test_passages_in_a_dropped_note_do_not_shift_the_others():
    r = records(f'<p xml:id="u9.9.9.9-p1">First <note type="side" n="1" xml:id="u9.9.9.9-n1">{la(1, "nota bene")}'
                f'</note>words here, {la(2, "dulce et decorum")}, it is sweet and fitting.</p>')
    assert spans(r["9.9.9.9-f2"])["following"] == "it is sweet and fitting"


def test_selector_extends_until_unique():
    text = "he is sick, he is sick, and he is sick."
    sel = selftrans.selector(text, text.rindex("he is sick"), len(text) - 1, "x")
    assert text.count(sel["prefix"] + sel["exact"] + sel["suffix"]) == 1


# ---------------------------------------------------------------- V7

def test_v7_checks_selftrans_selectors(tmp_path, monkeypatch):
    body = (f'<p xml:id="u9.9.9.9-p1">elsewhere he saith, {la(1, "morborum infinita multitudo")}, their number is '
            f'infinite.</p>')
    (tmp_path / "text").mkdir()
    (tmp_path / "text" / "9.9.9.9.xml").write_bytes(etree.tostring(unit(body)))
    monkeypatch.setattr(paths, "TEXT", tmp_path / "text")
    monkeypatch.setattr(paths, "LAYERS", tmp_path / "layers")
    selftrans.build(["9.9.9.9"])
    ok = layers.v7_layers(["9.9.9.9"])
    assert ok.ok, ok.problems
    assert ok.counts["selftrans_records"] == 1 and ok.counts["selftrans_selectors_ok"] == 1

    f = tmp_path / "layers" / "selftrans" / "9.9.9.9.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    data["9.9.9.9-f1"]["candidates"][0]["selector"]["exact"] = "their number is finite"
    f.write_text(json.dumps(data), encoding="utf-8")
    bad = layers.v7_layers(["9.9.9.9"])
    assert not bad.ok and bad.counts["selftrans_selectors_bad"] == 1

    f.write_text("{}", encoding="utf-8")
    missing = layers.v7_layers(["9.9.9.9"])
    assert not missing.ok and missing.counts["selftrans_missing"] == 1

    # V7's own bracket guard (independent of the layer code)
    assert layers._inside_brackets("a [b c] d", 4, 5) and not layers._inside_brackets("a [b c] d", 8, 9)


def test_ids_are_public():
    r = records(f'<p xml:id="u9.9.9.9-p1">{la(1, "dulce et decorum")}, it is sweet and fitting.</p>')
    assert list(r) == ["9.9.9.9-f1"] and not any(k.startswith("u") for k in r)
    assert r["9.9.9.9-f1"]["candidates"][0]["selector"]["in"] == "9.9.9.9-p1"
