"""Project paths. Everything is resolved from the repository root."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "data"
SOURCE = DATA / "source"
EPUB_COPY = SOURCE / "anatomy-gowland-2021.epub"
SOURCE_LOCK = SOURCE / "SOURCE.lock"
FONTS_SRC = SOURCE / "fonts"
FONTS_LOCK = SOURCE / "FONTS.lock"

WORK = ROOT / "work"
EPUB_DIR = WORK / "epub"  # unzipped EPUB
XHTML = EPUB_DIR / "EPUB" / "xhtml"
IMAGES = EPUB_DIR / "EPUB" / "images"

TEXT = DATA / "text"
LAYERS = DATA / "layers"
MANUAL = DATA / "manual"
IDS = DATA / "ids" / "registry.tsv"
GLOSSARY = DATA / "glossary.yaml"

SCHEMA = ROOT / "schema"
VERIFY = ROOT / "verify"
REPORTS = VERIFY / "reports"
STATE = ROOT / "state"
SITE = ROOT / "site"

DEFAULT_EPUB = Path(
    "C:/Users/Grood/Calibre Library/Robert Burton/The Anatomy of Melancholy (1423)/"
    "The Anatomy of Melancholy - Robert Burton.epub"
)
