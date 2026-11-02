"""M6 source verifier (burton/layers/sources.py) on a synthetic corpus: verified only on a real text match."""

from burton.layers import sources as S


def _corpus(tmp_path):
    d = tmp_path / "test" / "horace"
    d.mkdir(parents=True)
    (d / "odes.txt").write_text("3.6.46\tAetas parentum, peior avis, tulit nos nequiores, mox daturos "
                                "progeniem vitiosiorem.\n1.7.31\tnunc vino pellite curas\n", encoding="utf-8")
    units = S.load_corpora(tmp_path)
    return units, S.index(units)


def test_norm_merges_spellings():
    assert S.norm("Jupiter, vitæ  Æneas") == ["iupiter", "uite", "eneas"]
    assert S.norm("coelum foelix quum") == S.norm("caelum felix cum")


def test_verified_match_with_burtons_spelling(tmp_path):
    units, ix = _corpus(tmp_path)
    m = S.match(S.norm("mox daturi progeniem vitiosiorem"), units, ix)
    assert m is None  # 4 words: too short to verify
    m = S.match(S.norm("tulit nos nequiores, mox daturos progeniem vitiosiorem"), units, ix)
    assert m["author"] == "horace" and m["locus"] == "3.6.46" and m["cover"] == 1.0


def test_paraphrase_is_not_verified(tmp_path):
    units, ix = _corpus(tmp_path)
    assert S.match(S.norm("aetas parentum peior avis genuit nos multo deteriores"), units, ix) is None


def test_no_corpus_verifies_nothing(tmp_path):
    assert S.run(["1.1.1.2"], root=tmp_path / "none") == {"corpus_units": 0, "corpora": 0}
