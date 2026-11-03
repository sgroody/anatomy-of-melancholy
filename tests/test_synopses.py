"""M7 synopses: label resolution in the builder, and V11 catching a broken tree."""

import json
import shutil

import pytest

from burton import paths
from burton.ingest import synopses as S
from burton.verify import synopses as V

UNITS = ["1.1.1.1", "1.1.1.5", "1.1.2.1", "1.1.3.1", "1.1.3.2", "1.2.1.1", "1.2.5.1", "1.3.2.1"]


def test_labels_inherit_missing_levels():
    refs, after = S.resolve("Its Equivocations, in Disposition, Improper, &c., Subsect. 5.", [1, 1, 1, 4], UNITS)
    assert [r["unit"] for r in refs] == ["1.1.1.5"] and after == [1, 1, 1, 5]


def test_adjacent_labels_are_one_reference_in_either_order():
    for text in ("Continent, inward, antecedent, nearest. Memb. 5 Sect. 2.", "Particular causes Sect. 2 Memb. 5."):
        refs, after = S.resolve(text, [1, None, None, None], UNITS)
        assert [(r["div"], r["unit"]) for r in refs] == [("1.2.5", "1.2.5.1")] and after == [1, 2, 5, None]


def test_a_division_points_to_its_first_unit_and_a_list_to_each():
    refs, _ = S.resolve("Memb. 3. Its definition, name, difference, Subsect. 1.", [1, 1, 2, 1], UNITS)
    assert [(r["div"], r["unit"]) for r in refs] == [("1.1.3", "1.1.3.1"), ("1.1.3.1", "1.1.3.1")]
    refs, _ = S.resolve("Particular to private persons, according to Subsect. 3, 4.", [1, 1, 3, None], UNITS)
    assert [r["div"] for r in refs] == ["1.1.3.3", "1.1.3.4"]


def test_unknown_levels_and_missing_units_stay_unresolved():
    refs, _ = S.resolve("Habits, as Subsect. 4.", [1, None, None, None], UNITS)
    assert refs[0]["unit"] is None  # no section or member to inherit: never guessed
    refs, _ = S.resolve("Subsect. 9.", [1, 1, 1, None], UNITS)
    assert refs[0] == {"label": "Subsect. 9", "div": "1.1.1.9", "unit": None}
    refs, _ = S.resolve("Definition, Member, Division, Subsect. 2.", [1, 1, 1, None], UNITS)
    assert len(refs) == 1  # "Member," is a word, not a label


needs_epub = pytest.mark.skipif(not paths.XHTML.exists() or not (paths.DATA / "synopses" / "p1.json").exists(),
                                reason="needs the unpacked EPUB and a built data/synopses/p1.json")


def _copy(tmp_path, monkeypatch):
    (tmp_path / "synopses").mkdir()
    (tmp_path / "ids").mkdir()
    shutil.copy(paths.DATA / "synopses" / "p1.json", tmp_path / "synopses" / "p1.json")
    shutil.copy(paths.IDS, tmp_path / "ids" / "registry.tsv")
    monkeypatch.setattr(paths, "DATA", tmp_path)
    return tmp_path / "synopses" / "p1.json"


def _p1_problems():
    return [p for p in V.v11_synopses().problems if p.startswith("p1:")]


@needs_epub
def test_v11_passes_the_built_p1(tmp_path, monkeypatch):
    _copy(tmp_path, monkeypatch)
    assert _p1_problems() == []


@needs_epub
def test_v11_catches_a_dropped_node_an_edited_text_and_a_wrong_ref(tmp_path, monkeypatch):
    f = _copy(tmp_path, monkeypatch)
    tree = json.loads(f.read_text(encoding="utf-8"))
    first = tree["children"][0]
    dropped = first["children"][0]["children"].pop()  # Instrumental; and its child
    second = first["children"][1]
    second["text"][0]["t"] = second["text"][0]["t"].replace("Division", "Divisions")
    second["ref"][0]["unit"] = "1.1.1.3"
    f.write_text(json.dumps(tree, ensure_ascii=False), encoding="utf-8")
    problems = " | ".join(_p1_problems())
    assert dropped["src_p"] in problems and "unused" in problems
    assert "text differs from the EPUB" in problems
    assert "does not match the label" in problems


@needs_epub
def test_v11_rejects_an_unexplained_duplicate(tmp_path, monkeypatch):
    f = _copy(tmp_path, monkeypatch)
    tree = json.loads(f.read_text(encoding="utf-8"))
    tree["duplicates"][0]["reason"] = ""
    f.write_text(json.dumps(tree, ensure_ascii=False), encoding="utf-8")
    assert any("unexplained duplicate nat0000108" in p for p in _p1_problems())


def test_ordinal_labels_and_a_leading_number_at_a_given_level():
    units = ["2.2.1.1", "2.2.1.2", "2.2.2.1", "2.4.1.4"]
    refs, after = S.resolve("Diet rectified 1st Memb.", [2, 2, None, None], units)
    assert [r["unit"] for r in refs] == ["2.2.1.1"] and after == [2, 2, 1, None]
    refs, _ = S.resolve("2nd. Quantity.", [2, 2, 1, 1], units, num="subsect")
    assert [(r["label"], r["unit"]) for r in refs] == [("2nd.", "2.2.1.2")]
    refs, _ = S.resolve("2nd. Rectification of Retention and Evacuation", [2, 2, 1, None], units, num="memb")
    assert [r["unit"] for r in refs] == ["2.2.2.1"]
    refs, _ = S.resolve("4th. Subsect. Precious stones", [2, 4, 1, 3], units)
    assert [r["unit"] for r in refs] == ["2.4.1.4"]
    refs, _ = S.resolve("2nd. Quantity.", [2, 2, 1, 1], units)
    assert refs == []  # without `num` a bare number is not a label


@needs_epub
def test_v11_wants_a_reason_for_a_supplied_key(tmp_path, monkeypatch):
    if not (paths.DATA / "synopses" / "p2.json").exists():
        pytest.skip("p2 not built")
    shutil.copytree(paths.DATA / "synopses", tmp_path / "all")
    _copy(tmp_path, monkeypatch)
    f = tmp_path / "synopses" / "p2.json"
    tree = json.loads((tmp_path / "all" / "p2.json").read_text(encoding="utf-8"))
    supplied = next(t for t in tree["children"] if t.get("key", {}).get("supplied"))
    f.write_text(json.dumps(tree, ensure_ascii=False), encoding="utf-8")
    assert not [p for p in V.v11_synopses().problems if p.startswith("p2:")]
    supplied["key"]["supplied"] = ""
    f.write_text(json.dumps(tree, ensure_ascii=False), encoding="utf-8")
    assert any("does not print, with no reason" in p for p in V.v11_synopses().problems)


@needs_epub
def test_reader_links_only_built_units_and_every_unit_has_a_node():
    from burton.site import synopsis as R

    tree = R.load("p1")
    html = R.tree_html(tree, "../../", {"1.1.1.1": "1.1.1.1 Of the Causes"})
    assert 'href="../../1.1.1.1/"' in html and 'href="../../1.1.1.2/"' not in html
    assert '<span class="syn-ref">1.1.1.2</span>' in html  # named, but unlinked in a partial build
    assert '<span lang="grc">Φιλαργυρία</span>' in html
    units = sorted(p.stem for p in paths.TEXT.glob("[123].*.xml"))
    back = R.back_links(["p1", "p2", "p3"], units)
    assert set(back) == set(units)
    assert back["3.2.1.2"] == back["3.2.1.1"]  # no head of its own: it links to "Memb. 1."
