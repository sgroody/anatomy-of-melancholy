"""The Psalm check (burton/layers/psalm_check.py): Vulgate numbers and the verses offered."""

import pytest

from burton.layers import psalm_check as pc
from burton.site import kjv


def test_vulgate_numbers_map_to_the_kjv():
    assert pc.vulgate_to_kjv(5) == [5]
    assert pc.vulgate_to_kjv(9) == [9, 10]  # the Vulgate's 9 is the KJV's 9 and 10
    assert pc.vulgate_to_kjv(118) == [119]
    assert pc.vulgate_to_kjv(113) == [114, 115]
    assert pc.vulgate_to_kjv(147) == [147]


@pytest.mark.skipif(not (kjv.DIR / "pg10.txt").exists(), reason="data/source/kjv not present")
def test_candidates_put_burtons_number_first():
    cs = pc.candidates({"chapter": 118, "verses": [140]})
    assert cs[0]["id"] == "vulg-119-140" or cs[0]["id"] == "kjv"
    ids = [c["id"] for c in cs]
    assert "vulg-119-140" in ids and "Thy word is very pure" in next(c["text"] for c in cs if c["id"] == "vulg-119-140")
    assert pc.candidates({"chapter": 49, "verses": [20]})[0]["id"] == "kjv"
