"""Build-time soft hyphens for Latin and Greek (SPEC §7.2).

Browsers do not hyphenate `la` or `grc` (see tests/browser/test_hyphenation.py), so the renderer
inserts U+00AD into words inside those spans only. English is left to `hyphens: auto`.
Patterns: Latin from hyph-utf8 (Beccari, MIT; hyph_la.LICENSE.txt), Greek from Pyphen's el_GR,
which handles polytonic text. Soft hyphens exist only in the generated HTML, never in data/text.
"""

from functools import cache
from pathlib import Path

import pyphen
import regex

SHY = chr(0xAD)  # soft hyphen
HERE = Path(__file__).parent
WORD = regex.compile(r"\p{L}[\p{L}\p{M}]*")
MIN_LEN = 6  # shorter words are never broken


@cache
def dictionary(lang: str) -> pyphen.Pyphen | None:
    if lang == "la":
        return pyphen.Pyphen(filename=str(HERE / "hyph_la.dic"), left=2, right=3)
    if lang in ("grc", "el"):
        return pyphen.Pyphen(lang="el_GR", left=2, right=3)
    return None


@cache
def _word(lang: str, w: str) -> str:
    return dictionary(lang).inserted(w, hyphen=SHY)


def soft_hyphenate(text: str, lang: str | None) -> str:
    if not text or not lang or dictionary(lang) is None:
        return text
    return WORD.sub(lambda m: _word(lang, m.group(0)) if len(m.group(0)) >= MIN_LEN else m.group(0), text)
