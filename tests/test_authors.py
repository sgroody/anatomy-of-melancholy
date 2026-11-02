"""M6 author registry and pages: dates come only from a unique Wikidata match."""

from burton.layers import wikidata
from burton.site import authors_pages as A


def test_dates_only_from_a_match():
    assert A.dates({"status": "matched", "born": -65, "died": -8}) == "65 BC–8 BC"
    assert A.dates({"status": "matched", "born": -43, "died": 17}) == "43 BC – AD 17"
    assert A.dates({"status": "matched", "born": 1501, "died": 1576}) == "1501–1576"
    assert A.dates({"status": "matched", "born": None, "died": 1576}) == "d. 1576"
    assert A.dates({"status": "ambiguous", "candidates": [{"born": 1, "died": 2}]}) is None
    assert A.dates(None) is None


def test_names_split_latin_form():
    assert wikidata.names("André du Laurens (Laurentius)") == ["André du Laurens", "Laurentius"]
    assert wikidata.names("Horace") == ["Horace"]
