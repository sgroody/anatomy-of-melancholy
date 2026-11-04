from burton.layers import citations_inline as ci


def spans(text):
    return [text[f["start"]:f["end"]] for f in ci.scan_block(text)]


def test_author_with_locus_in_the_running_text():
    t = "and hot, as Avicenna lib. 3 Fen 1 Tract. 4 cap. 18 holds, it is a cause"
    assert spans(t) == ["Avicenna lib. 3 Fen 1 Tract. 4 cap. 18"]


def test_bible_book_with_numbers_after_a_stop():
    assert spans("’Tis all for your sins, Hag. 1. 9, 10, God is angry") == ["Hag. 1. 9, 10"]


def test_a_name_alone_is_not_a_citation():
    assert spans("the marvel of marvels, as Plato, the Abridgement of the World") == []


def test_a_bible_form_before_a_title_is_not_scripture():
    assert spans("as Salmuth com. in Pancirol. Tit. 10 de Horol. relates") == []


def test_prose_after_a_name_is_not_a_locus():
    assert spans("Labeo in Gellius, an ill habit of the body") == []


def test_the_citation_stops_at_a_colon_and_drops_a_joining_word():
    t = "St. Austin ep. 52 ad Macedonium, cap. 61 ad Dulcitium Tribunum: so doth Jerome"
    assert spans(t) == ["Austin ep. 52 ad Macedonium, cap. 61 ad Dulcitium Tribunum"]
    assert spans("used every morning. Montaltus cap. 26 and Jason Pratensis use") == ["Montaltus cap. 26"]
