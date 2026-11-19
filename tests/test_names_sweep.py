from burton.layers import names_sweep


def test_name_runs_are_split_into_forms():
    assert names_sweep._forms_of("Jason Pratensis, Laurentius, Montaltus, T. Bright") == [
        "Jason Pratensis", "Laurentius", "Montaltus", "T. Bright"]
    assert names_sweep._forms_of("Hercules de Saxonia") == ["Hercules de Saxonia"]
    assert names_sweep._forms_of("Pandora’s") == ["Pandora"]
    # not names: lower-case words, or a capitalised word followed by ordinary words
    assert names_sweep._forms_of("melancholy") == []
    assert names_sweep._forms_of("Melancholy in disposition") == []


def test_only_obscure_identified_single_bearers_are_shown():
    base = {"kind": "person", "obscure": True, "same": True, "status": "identified", "who": "x"}
    assert names_sweep.shown(base)
    assert not names_sweep.shown({**base, "obscure": False})
    assert not names_sweep.shown({**base, "same": False})
    assert not names_sweep.shown({**base, "status": "unidentified", "who": None})
    assert not names_sweep.shown({**base, "kind": "not-a-name"})
    assert names_sweep.shown({**base, "status": "probable"})


def test_restored_note_lines_label_every_machine_line():
    from burton.site.render import restored_lines

    rd = {"kind": "both", "tie": "partial", "burton_quote": "with wine and oil", "translation": "inwardly with mead",
          "citations": [{"raw": "Plin. lib. 7", "display": "Pliny, *Letters*, book 7", "status": "probable"},
                        {"raw": "x", "display": None, "status": "unidentified"}],
          "model": "m", "prompt": "restored-v1", "date": "2026-11-19"}
    counts = {}
    kind, lines = restored_lines(rd, counts)
    assert 'data-kind="note"' in kind
    assert "“with wine and oil”" in lines and "inwardly with mead" in lines
    assert "probably Pliny, <i>Letters</i>, book 7" in lines  # "probably" for an inferred work
    assert lines.count('class="prov"') == 3  # every added line carries its machine label
    assert counts["restored_citations"] == 1  # an unidentified reference is not shown


def test_a_gutenberg_note_repeating_gowlands_is_his():
    from burton.layers.restored_notes import repeats

    assert repeats("Lib. 7. Cum judicio, mores et facta recognoscit et se intuetur.",
                   "Pliny Epist. lib. 7. Cum judicio, mores & facta recognoscit, & se intuetur.")
    assert not repeats("Lib. 7.", "Lib. 7. Cum judicio")  # too few words to tell
    assert not repeats("Homo homini lupus, homo homini daemon.", "Plautus Asinaria.")
