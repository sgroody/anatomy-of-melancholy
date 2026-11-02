"""M6 citation parser (burton/layers/citations.py): rules over sidenote text, no model."""

from burton.layers import citations as C


def _one(text: str) -> dict:
    out = C.parse_note(text)
    assert len(out) == 1, out
    return out[0]


def test_fragmented_italics_merge_into_one_citation():
    # "<em>Scalig</em>. <em>exercit</em>. <em>365 sect</em>. <em>3</em>." reads as one citation
    c = C.parse_note("Scalig. exercit. 365 sect. 3. Vales. de sac. Phil. cap. 5.")
    assert [x["raw"] for x in c] == ["Scalig. exercit. 365 sect. 3.", "Vales. de sac. Phil. cap. 5."]
    assert c[0]["author"] == "scaliger-julius-caesar" and c[0]["resolved_by"] == "locus"
    assert c[0]["locus"] == [["exercitation", "365"], ["section", "3"]]
    assert c[1]["author"] == "valesius" and c[1]["locus"] == [["chapter", "5"]]


def test_locus_and_title_after_it():
    c = _one("Lib. 1 de increm. urb. cap. 6.")
    assert c["kind"] == "locus" and c["locus"] == [["book", "1"], ["chapter", "6"]]
    assert C._work("boterus", c["work_words"]) == "boterus.grandezza-citta"


def test_work_resolves_and_chapter_title_is_kept_apart():
    c = _one("Mercurialis de affect. capitis lib. 1 cap. 10 de Melanc.")
    assert c["author"] == "mercuriale" and C._work("mercuriale", c["work_words"]) == "mercuriale.de-affectibus"
    assert c["part_title"] == "de Melanc."


def test_prose_ends_a_citation():
    c = C.parse_note("Mercurialis, de affect. lib. 1 cap. 10, excepts all milkmeats in Hypochondriacal Melancholy.")
    assert [x["raw"] for x in c] == ["Mercurialis, de affect. lib. 1 cap. 10"]
    c = C.parse_note("Navig. lib. 2 cap. 4. Commercia nocte, hora secunda ob nimios aestus exercent.")
    assert c[0]["raw"] == "Navig. lib. 2 cap. 4."


def test_bible_needs_a_number_and_a_start():
    c = _one("Gen. 3. 17.")
    assert c["author"] == "bible" and c["work"] == "bible.genesis" and c["locus"] == [["n", "3"], ["n", "17"]]
    assert all(x["kind"] != "bible" for x in C.parse_note("De relig. lib. 1 Thes. 1."))


def test_ambiguous_forms_resolve_only_with_a_reason():
    assert _one("Plin. lib. 7 cap. 2.")["author"] == "pliny-elder"  # default, basis in the yaml
    assert _one("Plin. epist. 3 lib. 5.")["author"] == "pliny-younger"  # by its locator
    c = _one("Boethius lib. 1 Met. 1.")
    assert c["author"] is None and c["ambiguous_with"] == ["boethius", "boethius-hector"]


def test_unknown_name_is_unidentified_not_guessed():
    c = _one("Rosinus lib. 2. 19. Valerius lib. 2 cap. 1.".split(" Valerius")[0])
    assert c["author"] == "rosinus"
    c = _one("Palanterius.")
    assert c["kind"] == "unknown" and c.get("author") is None


def test_work_title_alone_names_its_author():
    c = _one("Mor. Encom.")
    assert c["kind"] == "unknown" and C._work_anywhere([c["head"], *c["work_words"]]) == ("erasmus", "erasmus.moria")


def test_no_citation_in_a_quotation():
    assert C.parse_note("Quid hoc ab insania deest?") == []
    assert C.parse_note("Christ Church in Oxford.") == []
