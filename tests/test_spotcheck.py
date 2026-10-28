"""M5 spot-check follow-ups: withdrawn source claims, and re-running named items."""

import pytest

from burton.translate import runner, validate

DECISIONS = {"u-f1": {"id": "u-f1", "reason": "the sidenote is anchored at the next quotation"}}


def test_a_withdrawn_source_claim_becomes_unidentified_and_keeps_what_it_replaced():
    src = {"status": "burton-cites", "author": "Virgil", "work": None, "locus": None,
           "basis": 'sidenote "Virg."', "verified": False}
    out = validate.apply_downgrade("u-f1", src, DECISIONS)
    assert out["status"] == "unidentified" and out["author"] is None
    assert out["downgraded_from"] == "burton-cites" and "next quotation" in out["decision"]
    assert validate.apply_downgrade("u-f2", src, DECISIONS) is src


def test_redo_needs_a_selection():
    with pytest.raises(SystemExit):
        runner._run(["1.1.1.2"], model="m", packet_size=1, max_packets=None, dry_run=True, redo=True)
