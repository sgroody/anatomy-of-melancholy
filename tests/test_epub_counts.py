"""The independent counter must reproduce the counts reported in SURVEY.md."""

import pytest

from burton import paths
from burton.verify import epub_counts

pytestmark = pytest.mark.skipif(not paths.XHTML.exists(), reason="run `burton unpack` first")


@pytest.fixture(scope="module")
def book():
    return epub_counts.book_counts(paths.XHTML)


def test_sidenotes(book):
    assert book["sidenote_refs"] + book["sidenote_refs_on_gowland_pages"] == 5703
    assert book["sidenote_bodies"] == 5703


def test_endnotes(book):
    assert book["endnote_refs"] + book["endnote_refs_on_gowland_pages"] == 3907
    assert book["endnote_bodies"] == 3907


def test_pagebreaks(book):
    assert book["pagebreaks"] + book["pagebreaks_on_gowland_pages"] == 959


def test_nav_units(book):
    assert book["nav_units"] == 149


def test_greek(book):
    # SURVEY: ~1,100 Greek characters overall (text + sidenotes); 20 of them are in a <title>.
    assert book["greek_chars_text"] == 872
    assert book["greek_chars_sidenotes"] == 213


def test_unit_1_1_1_2():
    c = epub_counts.unit_counts(paths.XHTML, "1.1.1.2")
    assert c["file"] == "chapter001-01"
    assert c["sidenote_numbers"] == list(range(55, 66))
    assert c["endnote_refs"] == 6
    assert c["heading_images"] == 1
