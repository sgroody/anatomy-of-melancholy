"""The front matter set facing Gowland (stage 9) and the click-through past the synopsis pages."""

from burton.site import facing
from burton.site.book import Book, text_units


def test_poems_pair_line_for_line_and_prose_by_paragraph():
    assert {k: len(v["rows"]) for k, v in facing.sources("ad-librum")["facing"].items()} == {"ad-librum-f2": 90}
    assert len(facing.sources("heraclite")["facing"]["heraclite-f1"]["rows"]) == 10
    lectori = facing.sources("lectori")
    assert len(lectori["facing"]["lectori-f2"]["rows"]) == 3  # a quoted line joins its paragraph
    assert lectori["heads"]["lectori-f1"] == "To the Mischievously Idle Reader."  # no "[Translation]"
    assert facing.sources("heraclite")["consumed"] and not facing.sources("ad-librum")["consumed"]


def test_gowland_notes_sit_on_the_rows_of_their_words():
    notes = facing.sources("ad-librum")["facing"]["ad-librum-f2"]["notes"]
    assert notes and all(1 <= k <= 90 for k in notes)


def test_next_goes_from_the_front_matter_into_the_text():
    book = Book("private", text_units())
    assert book.neighbours("heraclite")[1].key == "1.1.1.1"
    assert book.neighbours("dedication")[1].key == "ad-librum"  # not Gowland's translation page
    nxt = [book.neighbours(k)[1] for k in book.order if book.neighbours(k)[1]]
    assert not any(p.kind in ("partition", "synopsis") or p.gowland for p in nxt)
