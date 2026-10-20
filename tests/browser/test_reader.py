"""Browser tests of the built reader (private profile). Opt-in, since they need a build and Chrome:

    uv run burton build --all --profile private
    npm ci --prefix tests/browser
    uv run pytest -m browser

`burton check` runs the same checks (burton.verify.browser).
"""

import pytest

from burton import paths
from burton.verify import browser

pytestmark = [
    pytest.mark.browser,
    pytest.mark.skipif(not (paths.SITE / "private" / "index.html").exists(), reason="site/private is not built"),
]


def assert_ok(r):
    assert r.ok, f"{r.line()}\n" + "\n".join(r.problems[:20])


def test_offline_after_first_load():
    assert_ok(browser.offline_check())


def test_keyboard_walk_through():
    assert_ok(browser.keyboard_check())


def test_sidenote_layout_and_marker_lines():
    assert_ok(browser.layout_check())


def test_hyphenation_la_grc():
    assert_ok(browser.hyphenation_check())


@pytest.mark.skipif(not browser.AXE.exists(), reason="npm ci --prefix tests/browser")
def test_axe_20_pages():
    assert_ok(browser.axe_check())
