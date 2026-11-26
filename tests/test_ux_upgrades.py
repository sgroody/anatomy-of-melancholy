"""Tests for UX & elucidation site upgrades (F1-F5, E1-E5, V2-V6)."""

import json
import re

from burton import paths
from burton.layers import djs
from burton.site import glossary_page, labyrinth, render, synopsis
from burton.site.book import Book, text_units


def test_glossary_page_collect_covers_all_sections():
    data = glossary_page.collect({"horace": {"id": "horace"}})
    assert len(data["medical"]) >= 15
    assert len(data["apothecary"]) >= 7
    assert any(part["sym"] for row in data["apothecary"] for part in row["forms_parts"])
    assert len(data["locators"]) >= 9
    assert len(data["formulae"]) >= 4
    hor = next(a for a in data["authorities"] if a["name"] == "Horace")
    assert hor["author_id"] == "horace"


def test_labyrinth_doorways_and_sortes_pool():
    book = Book("public", text_units())
    words = {u: 1200 for u in book.units}
    html_ = labyrinth.doorways_html("", book.pages, words)
    assert 'href="2.2.3.1/"' in html_
    assert "~5 min" in html_
    pool = labyrinth.sortes_pool(book, words)
    keys = {entry["key"] for entry in pool}
    assert "3.2.3.1" in keys
    assert "table" not in keys
    assert "ad-librum-gowland" not in keys


def test_extract_signposts_strips_soft_hyphens_and_preserves_greek():
    sample = (
        '<span class="sidenote" id="u1-n1"><span class="sn-body">'
        '<span class="sn-n">a</span> <span class="sn-k" data-kind="note">note</span> '
        'Concerning <span class="fp" data-fid="u1-f1" data-lang="grc">'
        '<span class="fo" lang="grc">με\u00adλαγχολία</span>'
        '<span class="ft" role="note"><span class="sr-only">Translation from Greek: </span>'
        '<span class="ft-text">melancholy</span></span></span> and ancient writers.</span></span>'
        '<span class="sidenote sn-restored" id="u1-r1"><span class="sn-body">'
        '<span class="sn-n">b</span> <span class="sn-k" data-kind="note">note</span> '
        'Restored note must not appear as signpost.</span></span>'
        '<span class="sidenote" id="u1-n2"><span class="sn-body">'
        '<span class="sn-n">c</span> <span class="sn-k" data-kind="cites">cites</span> '
        'Galen cap. 3.'
        '</span></span>'
    )
    signs = synopsis.extract_signposts(sample)
    assert len(signs) == 1
    assert signs[0]["id"] == "u1-n1"
    assert "\u00ad" not in signs[0]["html"]
    assert "Translation from" not in signs[0]["html"]
    assert '<span lang="grc">μελαγχολία</span>' in signs[0]["html"]


def test_self_translation_literal_peek_is_v2h_and_v8_safe():
    from lxml import etree

    unit = "1.1.1.1"
    div = etree.parse(str(paths.TEXT / f"{unit}.xml")).getroot().find(".//{http://www.tei-c.org/ns/1.0}div")
    layer = json.loads((paths.LAYERS / "translations" / f"{unit}.json").read_text(encoding="utf-8"))
    djs_layer = json.loads((paths.LAYERS / "djs" / f"{unit}.json").read_text(encoding="utf-8"))
    cites = json.loads((paths.LAYERS / "citations" / f"{unit}.json").read_text(encoding="utf-8"))
    ic = json.loads((paths.LAYERS / "citations-inline" / f"{unit}.json").read_text(encoding="utf-8"))

    body_pub, _ = render.render_unit(
        div, unit, "public", layer, djs=djs_layer, cites=cites, inline_cites=ic,
    )
    # V2h invariant: ft-djs1927 and ft-gowland counts match layer expectations (literal uses ft-lit / mn-lit)
    expected_djs = sum(1 for k, r in djs_layer.items() if djs.shown(r, layer.get(k)))
    assert body_pub.count("ft-djs1927") == expected_djs
    assert 'data-resp="gowland"' not in body_pub
    assert "ft-lit" in body_pub or "mn-lit" in body_pub
    # Inline citation markers are button-role keyboard focusable
    for m in re.finditer(r'<span class="ic-m"[^>]*>', body_pub):
        assert 'tabindex="0"' in m.group(0)
        assert 'role="button"' in m.group(0)
