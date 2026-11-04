"""Rule gowland-kind-v1 on entries of the kinds found in Gowland's endnotes (examples written for the tests)."""

from lxml import etree

from burton.site import gowland_notes as gn
from burton.tei import ED, T


def test_pointers_to_another_note_or_to_the_book():
    assert gn.kind("bravely", "See above, n. 47 (DJR).") == "pointer"
    assert gn.kind("Alexander", "See above, n. 175 (DJR) and n. 30 (2.2.4).") == "pointer"
    assert gn.kind("Boors", "See above, nn. 181, 187 (1.2.3).") == "pointer"
    assert gn.kind("as I shall after show", "See below, 2.5.3.1.") == "pointer"
    assert gn.refs_in("See above, nn. 181, 187 (1.2.3).") == [("181", "1.2.3"), ("187", "1.2.3")]


def test_glosses_including_burtons_capitalised_nouns():
    assert gn.kind("margent", "Margin.") == "gloss"
    assert gn.kind("bursten-bellied", "That is, with a stomach swollen to the point of bursting.") == "gloss"
    assert gn.kind("Schools", "Universities.") == "gloss"
    assert gn.kind("personated", "Put (a person) forward in an assumed character; cf. above, n. 1 (DJR).") == "gloss"


def test_sources_of_quotations():
    assert gn.kind("Better marry than burn", "1 Corinthians 7:9.") == "source"
    assert gn.kind("Samson", "Judges 16.") == "source"
    assert gn.kind("good turn", "According to Diogenes Laertius (7.1.2–4), after Zeno was shipwrecked") == "source"
    assert gn.kind("Religion", "Of the Jews (Histories 5.13), where the phrase") == "source"


def test_a_pointers_chapter_label_is_not_a_locus():
    assert gn.kind("Antinous", "The constellation named by Hadrian after Antinous – on whom, see above, "
                               "n. 107 (1.2.4) – is now obsolete.") != "source"


def test_identities_and_explanations():
    assert gn.kind("Fallopius", "The eminent Italian anatomist and physician Gabriele Falloppio (1523–62).") == \
        "identity"
    assert gn.kind("took one dram for one scruple", "A triple dose, since in traditional weighting a dram is "
                   "roughly one-eighth of an ounce (3.54 grams).") == "explanation"


def test_a_lemma_split_by_an_ellipsis_is_mended():
    e = etree.Element(ED("endnote"))
    a = etree.SubElement(e, T("hi"), rend="i")
    a.text, a.tail = "Knight of the sun", ": See above, n. 249 (1.2.3). Suidas … "
    b = etree.SubElement(e, T("hi"), rend="i")
    b.text, b.tail = "in Pindar", ": A gloss of the scholiast."
    assert gn.segments(e) == [("Knight of the sun", "See above, n. 249 (1.2.3)."),
                              ("Suidas … in Pindar", "A gloss of the scholiast.")]
