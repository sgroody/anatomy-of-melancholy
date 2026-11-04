import pytest

from burton.layers import cite_expand as ce

ITEM = {"id": "u-n1-c1", "note": "Epist. lib. 6.", "citation": "Epist. lib. 6.", "rules": {"author": None,
        "expansion": None}, "context": "as ⟦sidenote⟧Plinius Secundus writes", "previous": "Seneca, letter 9"}


def answer(**kw):
    a = {"is_citation": True, "author_id": "pliny-younger", "author_name": "Pliny the Younger",
         "basis": "named-at-anchor", "evidence": "Plinius Secundus", "work": "Epistulae", "locus": "book 6",
         "display": "Pliny the Younger, Epistulae, book 6", "confidence": "high", "reason": "named at the marker"}
    return {**a, **kw}


def test_named_with_evidence_in_the_context_is_expanded():
    status, kept = ce.postcheck(ITEM, answer(), {"pliny-younger"})
    assert status == "expanded" and kept["author"] == "pliny-younger"


def test_evidence_not_in_the_input_fails():
    assert ce.postcheck(ITEM, answer(evidence="Pliny"), {"pliny-younger"})[0] == "failed-postcheck"


def test_low_confidence_or_no_basis_stays_unidentified():
    assert ce.postcheck(ITEM, answer(confidence="low"), set())[0] == "unidentified"
    assert ce.postcheck(ITEM, answer(basis="none"), set())[0] == "unidentified"


def test_inferred_from_the_work_is_only_probable():
    status, _ = ce.postcheck({**ITEM, "note": "Heaut. Act. 1"}, answer(basis="work-known", evidence="Heaut."), set())
    assert status == "probable"


def test_an_unknown_author_id_is_dropped_but_the_name_kept():
    status, kept = ce.postcheck(ITEM, answer(author_id="invented"), {"pliny-younger"})
    assert status == "expanded" and kept["author"] is None and kept["author_name"] == "Pliny the Younger"


def test_idem_needs_a_previous_citation():
    a = answer(basis="idem-previous", evidence=None)
    assert ce.postcheck(ITEM, a, set())[0] == "expanded"
    assert ce.postcheck({**ITEM, "previous": None}, a, set())[0] == "unidentified"


def test_a_bracket_in_the_payload_is_refused():
    with pytest.raises(SystemExit):
        ce.leak_check([{**ITEM, "note": "Epist. [Letters] lib. 6."}])
