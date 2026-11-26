"""Stage read-only mirror files and self-contained persona packets inside the current workspace.

Ensures child workflow agents running under workspace="inherit" NEVER call file tools outside
WORKSPACES[0] (preventing hidden permission-wait freezes when T3 Code's session workspace is
outside C:\\Users\\Grood\\Melancholy).

Usage:
    uv run python tools/human_ux_workflow/prepare_packets.py --stage-dir <STAGE_DIR>
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from lxml import html as lhtml

REPO = Path("C:/Users/Grood/Melancholy")


def numbered_slice(path: Path, start_line: int = 1, end_line: int | None = None) -> str:
    """Read lines [start_line..end_line] (1-based inclusive) with line numbers."""
    lines = path.read_text(encoding="utf-8").splitlines()
    hi = min(len(lines), end_line) if end_line else len(lines)
    lo = max(1, start_line)
    out = [f"{i}: {lines[i - 1]}" for i in range(lo, hi + 1)]
    return "\n".join(out)


def mirror_tree(stage_dir: Path) -> Path:
    """Copy key reference files into <stage_dir>/mirror so child agents can inspect safely."""
    mirror = stage_dir / "mirror"
    if mirror.exists():
        shutil.rmtree(mirror)
    mirror.mkdir(parents=True, exist_ok=True)

    rel_files = [
        "CLAUDE.md",
        "SPEC.md",
        "data/glossary.yaml",
        "state/review/to-revisit.md",
        "state/review/ab-2026-11-21-r9.html",
        "burton/site/frontispiece.py",
        "burton/site/book.py",
        "burton/site/authors_pages.py",
        "burton/site/synopsis.py",
        "burton/site/build.py",
        "burton/site/glosses.py",
        "burton/site/gowland_notes.py",
        "burton/site/facing.py",
        "burton/site/names.py",
        "burton/site/render.py",
        "burton/site/static/edition.css",
        "burton/site/static/edition.js",
        "burton/site/static/search.js",
    ]
    for tpl in (REPO / "burton" / "site" / "templates").glob("*.html"):
        rel_files.append(str(tpl.relative_to(REPO)).replace("\\", "/"))

    for rel in rel_files:
        src = REPO / rel
        if not src.exists():
            continue
        dst = mirror / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    for built_rel in [
        "site/private/index.html",
        "site/private/1.1.1.1/index.html",
        "site/private/3.2.3.1/index.html",
        "site/private/authors/index.html",
        "site/private/table/index.html",
    ]:
        src = REPO / built_rel
        if not src.exists():
            continue
        dst = mirror / built_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        txt = src.read_text(encoding="utf-8")
        if len(txt) > 65000:
            txt = txt[:65000] + "\n<!-- [truncated in mirror after 65 KB] -->\n"
        dst.write_text(txt, encoding="utf-8")

    return mirror


def extract_built_sample(rel: str, xpath_expr: str, max_items: int = 3) -> str:
    p = REPO / rel
    if not p.exists():
        return "(file missing)"
    tree = lhtml.fromstring(p.read_bytes())
    els = tree.xpath(xpath_expr)[:max_items]
    return "\n".join(lhtml.tostring(e, encoding="unicode")[:900] for e in els)


def build_packets(stage_dir: Path) -> list[Path]:
    packets_dir = stage_dir / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)

    p1 = "\n\n".join([
        "# Packet 1: Front Page, Navigation Gate & Visitor Onboarding",
        "## burton/site/templates/home.html\n```html\n" + numbered_slice(REPO / "burton/site/templates/home.html") + "\n```",
        "## burton/site/templates/front_key.html\n```html\n" + numbered_slice(REPO / "burton/site/templates/front_key.html") + "\n```",
        "## burton/site/templates/options.html\n```html\n" + numbered_slice(REPO / "burton/site/templates/options.html") + "\n```",
        "## burton/site/templates/about.html (lines 1-140)\n```html\n" + numbered_slice(REPO / "burton/site/templates/about.html", 1, 140) + "\n```",
        "## burton/site/static/edition.css (front page lines 762-960)\n```css\n" + numbered_slice(REPO / "burton/site/static/edition.css", 762, 960) + "\n```",
        "## burton/site/frontispiece.py (lines 1-140)\n```python\n" + numbered_slice(REPO / "burton/site/frontispiece.py", 1, 140) + "\n```",
        "## burton/site/book.py (lines 1-140)\n```python\n" + numbered_slice(REPO / "burton/site/book.py", 1, 140) + "\n```",
    ])

    p2 = "\n\n".join([
        "# Packet 2: Sustained Reading, Mobile/Tablet Parity & State Persistence",
        "## burton/site/static/edition.js (lines 1-380: settings, apply, popover, layoutNotes)\n```js\n" + numbered_slice(REPO / "burton/site/static/edition.js", 1, 380) + "\n```",
        "## burton/site/static/edition.js (lines 550-685: light/pin, translation click/touch, facing)\n```js\n" + numbered_slice(REPO / "burton/site/static/edition.js", 550, 685) + "\n```",
        "## burton/site/static/edition.js (lines 975-1135: preview windows, touch gating, frontispiece)\n```js\n" + numbered_slice(REPO / "burton/site/static/edition.js", 975, 1135) + "\n```",
        "## burton/site/static/edition.css (lines 1-240: theme, base, language colour media)\n```css\n" + numbered_slice(REPO / "burton/site/static/edition.css", 1, 240) + "\n```",
        "## burton/site/static/edition.css (lines 241-450 & 1300-1395: notes, popovers, mobile)\n```css\n" + numbered_slice(REPO / "burton/site/static/edition.css", 241, 450) + "\n\n" + numbered_slice(REPO / "burton/site/static/edition.css", 1300, 1395) + "\n```",
    ])

    p3 = "\n\n".join([
        "# Packet 3: Scholarly Research, Deep-Link Arrivals & Reference Indices",
        "## burton/site/static/search.js\n```js\n" + numbered_slice(REPO / "burton/site/static/search.js") + "\n```",
        "## burton/site/templates/search.html\n```html\n" + numbered_slice(REPO / "burton/site/templates/search.html") + "\n```",
        "## burton/site/templates/authors.html & author.html\n```html\n" + numbered_slice(REPO / "burton/site/templates/authors.html") + "\n\n" + numbered_slice(REPO / "burton/site/templates/author.html") + "\n```",
        "## burton/site/authors_pages.py\n```python\n" + numbered_slice(REPO / "burton/site/authors_pages.py") + "\n```",
        "## burton/site/render.py (lines 500-700: citations, foreign passages, burton_renders)\n```python\n" + numbered_slice(REPO / "burton/site/render.py", 500, 700) + "\n```",
        "## burton/site/static/edition.js (lines 333-458: layoutNotes & hash/scroll gap)\n```js\n" + numbered_slice(REPO / "burton/site/static/edition.js", 333, 458) + "\n```",
        "## Sample built DOM (3.2.3.1 sidenotes, Penguin pagebreak, Authors row)\n```html\n"
        + extract_built_sample("site/private/3.2.3.1/index.html", '//article//*[contains(@class,"sidenote")]', 2)
        + "\n"
        + extract_built_sample("site/private/authors/index.html", '//table//tbody/tr', 4)
        + "\n```",
    ])

    p4 = "\n\n".join([
        "# Packet 4: Serendipitous Dipping, Commonplacing & Labyrinth Navigation",
        "## burton/site/synopsis.py (lines 1-220)\n```python\n" + numbered_slice(REPO / "burton/site/synopsis.py", 1, 220) + "\n```",
        "## burton/site/build.py (lines 220-460: site pages, search index, back matter)\n```python\n" + numbered_slice(REPO / "burton/site/build.py", 220, 460) + "\n```",
        "## burton/site/templates/unit.html & page.html\n```html\n" + numbered_slice(REPO / "burton/site/templates/unit.html") + "\n\n" + numbered_slice(REPO / "burton/site/templates/page.html") + "\n```",
        "## data/glossary.yaml\n```yaml\n" + numbered_slice(REPO / "data/glossary.yaml") + "\n```",
    ])

    p5 = "\n\n".join([
        "# Packet 5: Elucidating Burton & Human Design Principles",
        "## burton/site/glosses.py\n```python\n" + numbered_slice(REPO / "burton/site/glosses.py") + "\n```",
        "## burton/site/gowland_notes.py (lines 1-160)\n```python\n" + numbered_slice(REPO / "burton/site/gowland_notes.py", 1, 160) + "\n```",
        "## burton/site/facing.py\n```python\n" + numbered_slice(REPO / "burton/site/facing.py") + "\n```",
        "## burton/site/render.py (lines 1-140 & 560-760: provenance signs, self-translation, glosses)\n```python\n" + numbered_slice(REPO / "burton/site/render.py", 1, 140) + "\n\n" + numbered_slice(REPO / "burton/site/render.py", 560, 760) + "\n```",
        "## data/glossary.yaml\n```yaml\n" + numbered_slice(REPO / "data/glossary.yaml") + "\n```",
        "## Sample built 3.2.3.1 passage with .fp, .burton-tr, .ic-m, .gl-w, .mn-gw\n```html\n"
        + extract_built_sample("site/private/3.2.3.1/index.html", '//article//p[@id="3.2.3.1-p1" or @id="3.2.3.1-p60"]', 2)
        + "\n```",
    ])

    p6 = "\n\n".join([
        "# Packet 6: Book Typography, Print Craft & To-Revisit Decisions (P3 & H2)",
        "## state/review/to-revisit.md\n```markdown\n" + numbered_slice(REPO / "state/review/to-revisit.md") + "\n```",
        "## burton/site/static/edition.css (lines 450-760: tooltips, print, two-side, headings)\n```css\n" + numbered_slice(REPO / "burton/site/static/edition.css", 450, 760) + "\n```",
        "## burton/site/static/edition.css (lines 1080-1395: syn-badge, mn-fold, P3 rubric rule, edge turners)\n```css\n" + numbered_slice(REPO / "burton/site/static/edition.css", 1080, 1395) + "\n```",
        "## burton/site/static/edition.js (lines 160-225: header search, settings, TOC keyboard Escape handlers)\n```js\n" + numbered_slice(REPO / "burton/site/static/edition.js", 160, 225) + "\n```",
        "## burton/site/static/edition.js (lines 685-942: synopses rest/grow pace & ?uid/?fm)\n```js\n" + numbered_slice(REPO / "burton/site/static/edition.js", 685, 942) + "\n```",
        "## burton/site/static/edition.js (lines 1065-1100: POP hover gating on wide.matches vs openName keyboard handler)\n```js\n" + numbered_slice(REPO / "burton/site/static/edition.js", 1065, 1100) + "\n```",
    ])

    written = []
    for idx, content in enumerate([p1, p2, p3, p4, p5, p6], start=1):
        out = packets_dir / f"persona_{idx}.md"
        out.write_text(content, encoding="utf-8")
        written.append(out)
    return written


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", required=True)
    args = parser.parse_args()
    stage_dir = Path(args.stage_dir)
    stage_dir.mkdir(parents=True, exist_ok=True)
    mirror = mirror_tree(stage_dir)
    packets = build_packets(stage_dir)
    print(f"Staged mirror at {mirror} and {len(packets)} persona packets in {stage_dir / 'packets'}")


if __name__ == "__main__":
    main()
