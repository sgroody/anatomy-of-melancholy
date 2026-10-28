"""Dell & Jordan-Smith alignment: page furniture, their attributions, kept originals, what the reader shows."""

from burton.layers import djs

PAGE = ("they consume the interim of their time, a beg-\n\n"
        "*  Joh.  Howson,  4  Novembris,  1597.  —  Burton's  note. \n\n\n"
        "Memb.3,Subs.  IS]       ThE     MISERIES     OF     SCHOLARS        [269 \n\n"
        "gar's brat taken from the bridge. Thus far \n\n\n132  ] \n\n\n"
        "Anatomy   of    Melancholy    [Part,  i,  Sect,  i \n\n"
        "the text goes on (horace) Mcmb.3] Remedies Against Discontents [525 and on.\n")


def test_page_furniture_is_skipped_and_words_rejoin_across_it():
    d = djs.Djs(PAGE)
    text = " ".join(d.words)
    assert "beggar's brat" in text
    for gone in ("Howson", "MISERIES", "269", "132", "Anatomy", "Remedies", "525"):
        assert gone not in text
    assert [p for _, p in d.heads] == [269, 132]


def test_their_attribution_and_footnote_mark_are_kept_apart():
    assert djs.split_attribution("Lost money is bewept with genuine tears, (juvenal)") == (
        "Lost money is bewept with genuine tears,", "juvenal")
    assert djs.split_attribution("(by the permission of God)") == ("(by the permission of God)", None)


def test_kept_originals_and_broken_spans_are_recognised():
    assert djs._kept("Heautontimorumenoi", "Heautontimorumenoi,'^")
    assert not djs._kept("Philtrum", "philter")
    assert djs._broken_brackets("Pius II., in his Boccacian novel] observes) any")
    assert not djs._broken_brackets("Chorus Sancti Viti [St. Vitus Dance].")
    assert not djs._is_words("E«5,")


def test_the_reader_shows_only_current_alignments_burton_does_not_render_himself():
    rec = {"status": "aligned", "text_sha1": "s", "text": "born to themselves", "method": "m",
           "where": "IA x djvu.txt line 9, p. 173"}
    tr = {"text_sha1": "s", "self_translation": {"status": "none"}}
    assert djs.shown(rec, tr) and djs.version(rec)["page"] == "173"
    assert not djs.shown(rec, {**tr, "self_translation": {"status": "full"}})
    assert not djs.shown(rec, {**tr, "text_sha1": "t"})
    assert not djs.shown({**rec, "status": "kept-original"}, tr)
