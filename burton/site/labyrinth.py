"""Curated doorways into The Anatomy of Melancholy and Sortes Burtonianae (V2).

Every doorway keeps Burton's own title and unit key from burton.site.book; reading times are
computed from the built units' public word counts (so a partial build shows only its own
doorways and real word-count estimates).
"""

import json

from .render import attr, esc

WPM = 220

DOORWAYS: list[tuple[str, str, str]] = [
    ("djr", "Democritus Junior to the Reader",
     "Burton’s playful self-portrait and satirical utopia — the great doorway into the whole book."),
    ("abstract", "The Author’s Abstract of Melancholy",
     "A poem alternating the sweets and damps of melancholy before the prose begins."),
    ("1.2.1.2", "A Digression of the Nature of Spirits",
     "How seventeenth-century demonology accounts for spirits, witches, and despair."),
    ("1.2.3.15", "Digression of the Misery of Scholars",
     "Why the Muses are melancholy: patrons, poverty, neglect, and the scholar’s lot."),
    ("2.2.3.1", "A Digression of the Air",
     "An imaginary flight over earth and heavens weighing climates, winds, and stars."),
    ("2.2.4.1", "Exercise Rectified of Body and Mind",
     "Walks, chess, gardens, studies, and honest recreations prescribed against sadness."),
    ("2.2.6.3", "Music a Remedy",
     "How song and instruments calm troubled spirits and draw melancholy out."),
    ("2.3.1.1", "A Consolatory Digression",
     "Philosophical remedies for poverty, exile, grief, and every worldly reverse."),
    ("3.2.1.1", "Heroical Love: Pedigree, Power, and Extent",
     "Love as the supreme madness running through the Third Partition."),
    ("3.2.3.1", "Symptoms of Love-Melancholy",
     "Pale looks, sighs, sleeplessness, poetry, and lovers’ contradictions."),
    ("3.3.1.1", "Jealousy",
     "How suspicion feeds upon love across nations, households, and imaginations."),
    ("3.4.1.1", "Religious Melancholy",
     "False zeal, superstition, despair, and the closing counsel: be not solitary, be not idle."),
]


def read_minutes(words: int) -> int:
    return max(1, round(words / WPM)) if words > 0 else 1


def florilegium_list_html(root: str, book_pages: dict, words_by_unit: dict[str, int] | None = None) -> str:
    """List of curated Florilegium passages with reading times."""
    items = []
    for uid, label, blurb in DOORWAYS:
        pg = book_pages.get(uid)
        if not pg:
            continue
        w = (words_by_unit or {}).get(uid, 0)
        mins = f' <span class="lab-time">~{read_minutes(w)} min</span>' if w else ""
        items.append(
            f'<li class="lab-item"><a href="{attr(root + pg.href)}">'
            f'<span class="lab-t">{esc(label)}</span>{mins}</a>'
            f'<span class="lab-note">{esc(blurb)}</span></li>'
        )
    if not items:
        return ""
    return f'<ul class="lab-list">{"".join(items)}</ul>'


def doorways_html(root: str, book_pages: dict, words_by_unit: dict[str, int] | None = None) -> str:
    lst = florilegium_list_html(root, book_pages, words_by_unit)
    if not lst:
        return ""
    return (
        '<details class="toc-ways">'
        '<summary>Florilegium — celebrated passages</summary>'
        f'{lst}'
        '</details>'
    )


def sortes_pool(book, words_by_unit: dict[str, int] | None = None) -> list[dict]:
    """Units eligible for Sortes Burtonianae ("Open at a venture"), excluding Gowland-only sheets."""
    pool = []
    for u in book.units:
        pg = book.pages.get(u)
        if not pg or pg.gowland or u == "table":
            continue
        w = (words_by_unit or {}).get(u, 0)
        pool.append({
            "key": u,
            "href": pg.href,
            "title": f"{pg.number} {pg.title}" if pg.number else pg.title,
            "mins": read_minutes(w) if w else None,
        })
    return pool


def contents_extras_html(root: str, book, words_by_unit: dict[str, int] | None = None, *,
                         has_sortes: bool = True) -> str:
    """Folded doorways and Sortes Burtonianae tucked inside the Contents menu."""
    ways = doorways_html(root, book.pages, words_by_unit)
    sortes = ""
    if has_sortes and any(not book.pages[u].gowland and u != "table" for u in book.units if u in book.pages):
        sortes = '<button type="button" class="sortes-btn">Open at a venture</button>'
    if not ways and not sortes:
        return ""
    return (
        '<div class="toc-extras" role="region" aria-label="Ways into the book">'
        f'<div class="toc-ex-bar">{sortes}</div>'
        f'{ways}'
        '</div>'
    )


def write_sortes(pool: list[dict], dest) -> int:
    data = json.dumps(pool, ensure_ascii=False, separators=(",", ":"))
    dest.write_text(data, encoding="utf-8", newline="\n")
    return len(data.encode("utf-8"))
