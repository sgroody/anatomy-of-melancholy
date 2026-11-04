"""Self-hosted fonts: fetch OFL sources once (pinned by sha256), subset them at build time."""

import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont

from .. import paths
from ..source import sha256

BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl"
SOURCES = {
    "EBGaramond-Roman.ttf": f"{BASE}/ebgaramond/EBGaramond%5Bwght%5D.ttf",
    "EBGaramond-Italic.ttf": f"{BASE}/ebgaramond/EBGaramond-Italic%5Bwght%5D.ttf",
    "EBGaramond-OFL.txt": f"{BASE}/ebgaramond/OFL.txt",
    # Fallback for what EB Garamond lacks: apothecary signs (℥ ℈), planets and zodiac (☉ ☌ ♄ ♎ …), ⁂.
    # Cardo is a scholarly OFL serif for classicists; it covers every one of them.
    "Cardo-Regular.ttf": f"{BASE}/cardo/Cardo-Regular.ttf",
    "Cardo-OFL.txt": f"{BASE}/cardo/OFL.txt",
    # Greek in its own face (owner, 2026-11-03: T10 B): GFS Didot, from the Greek Font Society
    "GFSDidot-Regular.ttf": f"{BASE}/gfsdidot/GFSDidot-Regular.ttf",
    "GFSDidot-OFL.txt": f"{BASE}/gfsdidot/OFL.txt",
}
# Built faces: (css family, style, source file)
FACES = [("EB Garamond", "normal", "EBGaramond-Roman.ttf"), ("EB Garamond", "italic", "EBGaramond-Italic.ttf")]
FALLBACK = ("Burton Symbols", "normal", "Cardo-Regular.ttf")
STACK = '"EB Garamond", "Burton Symbols", Garamond, Georgia, serif'
FEATURES = ["kern", "liga", "clig", "calt", "smcp", "c2sc", "onum", "pnum", "ccmp", "mark", "mkmk", "locl"]


def read_lock() -> dict:
    if not paths.FONTS_LOCK.exists():
        return {}
    return dict(reversed(line.split(maxsplit=1)) for line in
                paths.FONTS_LOCK.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#"))


def fetch() -> None:
    paths.FONTS_SRC.mkdir(parents=True, exist_ok=True)
    lock = read_lock()
    lines = ["# sha256  file   (fonts under the SIL Open Font License; sources in fonts.py)"]
    for name, url in SOURCES.items():
        dest = paths.FONTS_SRC / name
        if not dest.exists():
            print(f"fetching {name} from {url}")
            with urllib.request.urlopen(url, timeout=60) as r:
                dest.write_bytes(r.read())
        digest = sha256(dest)
        if name in lock and lock[name] != digest:
            raise SystemExit(f"{name}: hash {digest} does not match FONTS.lock {lock[name]}")
        lines.append(f"{digest}  {name}")
        print(f"{name}: {dest.stat().st_size:,} bytes, sha256 {digest[:16]}…")
    paths.FONTS_LOCK.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def check_lock() -> None:
    lock = read_lock()
    for name in SOURCES:
        p = paths.FONTS_SRC / name
        if not p.exists():
            raise SystemExit(f"font source {name} missing: run `burton fonts`")
        if lock.get(name) != sha256(p):
            raise SystemExit(f"font source {name} does not match FONTS.lock")


def cmap(path) -> set[int]:
    return set(TTFont(str(path)).getBestCmap())


def build_subsets(codepoints: set[int], out_dir) -> list[dict]:
    """Subset each face to the code points used (plus basic punctuation); returns face records.
    The fallback face gets only the used code points that no EB Garamond face has."""
    check_lock()
    out_dir.mkdir(parents=True, exist_ok=True)
    keep = set(codepoints) | set(range(0x20, 0x7F)) | {0x2019, 0x2018, 0x201C, 0x201D, 0x2014, 0x2026, 0x27E8, 0x27E9}
    primary = set().union(*(cmap(paths.FONTS_SRC / src) for _, _, src in FACES))
    faces = []
    for family, style, src in FACES + [FALLBACK]:
        wanted = keep if src != FALLBACK[2] else set(codepoints) - primary
        if not wanted:
            continue
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = FEATURES
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        font = TTFont(str(paths.FONTS_SRC / src))
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=sorted(wanted & set(font.getBestCmap())))
        sub.subset(font)
        name = src.replace(".ttf", ".woff2")
        font.flavor = "woff2"
        font.save(str(out_dir / name))
        faces.append({"family": family, "style": style, "file": name, "cmap": cmap(out_dir / name),
                      "fallback": src == FALLBACK[2]})
    return faces
