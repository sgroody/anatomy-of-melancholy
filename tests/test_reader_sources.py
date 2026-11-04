"""The reader's translation sources: Gowland's versions in the private build only, every version listed,
and each translation that stands in for the original marked with its language."""

from lxml import etree

from burton.site import render
from burton.tei import NSMAP, TEI_NS

REC = {"lang": "la", "kind": "phrase", "location": "text", "text": "caecus amor sui", "text_sha1": "x",
       "self_translation": {"status": "none", "burton_span": None},
       "translations": [{"by": "machine", "model": "claude-opus-5-5", "prompt": "tr-v2", "date": "2026-10-23",
                         "text": "blind love of self", "note": None}],
       "source": {"status": "unidentified"}, "preferred": "machine"}


def div_of(blocks: str):
    return etree.fromstring(f'<div xmlns="{TEI_NS}" xmlns:ed="{NSMAP["ed"]}" xmlns:xml="http://www.w3.org/XML/1998/namespace">'
                            f"{blocks}</div>")


DIV = ('<p><foreign ana="foreign" xml:lang="la" xml:id="uu-f1"><hi rend="i">caecus amor sui</hi></foreign>'
       '<ed:trans for="uu-f1"> [blind <supplied>{self-}</supplied>love<note type="side" n="1">Hor.</note>]</ed:trans>'
       ', which</p>')


def render_div(profile: str, layer: dict) -> str:
    return render.render_unit(div_of(DIV), "u", profile, layer)[0]


def test_gowland_text_is_read_without_brackets_notes_or_braces():
    assert render.gowland_versions(div_of(DIV)) == {"u-f1": "blind self-love"}


def test_bracket_over_several_blocks_is_joined_from_its_pieces():
    div = div_of('<p><foreign ana="foreign" xml:lang="la" xml:id="uu-f2">Latine</foreign>'
                 '<ed:trans for="uu-f2" part="I"> [The translation begins</ed:trans></p>'
                 '<p><ed:trans part="M">goes on</ed:trans></p><p><ed:trans part="F">and ends here]</ed:trans>.</p>')
    assert render.gowland_versions(div) == {"u-f2": "The translation begins goes on and ends here"}


def test_private_box_lists_every_version_preferred_first_with_its_language():
    html = render_div("private", {"u-f1": REC})
    assert html.index("ft-gowland") < html.index("ft-machine")  # the default order: Gowland first (SPEC §6.3)
    assert "from Latin" in html and "Translation from Latin: " in html
    assert "Gowland 2021 (private build)" in html and "claude-opus-5-5" in html


def test_public_build_has_no_gowland_version():
    html = render_div("public", {"u-f1": REC})
    assert "ft-gowland" not in html and 'data-resp="gowland"' not in html and "self-love" not in html


def test_gowland_alone_makes_a_passage_translatable_in_the_private_build_only():
    assert "fp-untranslated" not in render_div("private", {})
    assert "fp-untranslated" in render_div("public", {})
