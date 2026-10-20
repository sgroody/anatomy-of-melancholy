"""The gold samples: hold-out rounds stay disjoint, and V5 gates on the newest one."""

from burton.verify import gold


def _keys(rows):
    return {(r["unit"], gold.norm(r["text"])) for r in rows}


def test_newest_round_is_the_gate():
    assert gold.GATE == gold.HOLDOUTS[-1]["name"]
    assert gold.HOLDOUT_GOLD == gold.HOLDOUTS[-1]["gold"]
    assert all(h.get("seen") for h in gold.HOLDOUTS[:-1])  # every earlier round says why it is no longer blind


def test_rounds_are_disjoint_from_each_other_and_from_tuning():
    seen = _keys(gold.read_gold()) | _keys(gold.read_sample(gold.SAMPLE))
    for h in gold.HOLDOUTS:
        rows = gold.read_sample(h["sample"])
        assert not _keys(rows) & seen, h["name"]
        seen |= _keys(rows)


def test_gold_labels_cover_their_sample():
    for h in gold.HOLDOUTS:
        if h["gold"].exists():
            assert {r["sid"] for r in gold.read_gold(h["gold"])} == {r["sid"] for r in gold.read_sample(h["sample"])}


def test_labelled_round_is_never_redrawn():
    h = gold.HOLDOUTS[-1]
    if h["gold"].exists():
        try:
            gold.draw_holdout(h["name"])
        except SystemExit:
            return
        raise AssertionError("draw_holdout overwrote a labelled round")


def test_a_deferred_check_still_reports_but_does_not_fail(tmp_path, monkeypatch):
    from burton.verify import checks

    monkeypatch.setattr(checks.paths, "REPORTS", tmp_path)
    monkeypatch.setattr(checks, "deferred_checks",
                        lambda: {"V5": {"decision": "D10", "date": "2026-10-20", "reason": "owner chose to move on"}})
    v5, v1 = checks.Result("V5", "language-ID"), checks.Result("V1", "text")
    v5.fail("held-out below target")
    assert checks.report([v5, v1], "t") is True
    assert v5.line().startswith("DEFER") and v5.problems  # never PASS, problems kept
    v1.fail("text differs")
    assert checks.report([v5, v1], "t") is False  # only the listed check is deferred
