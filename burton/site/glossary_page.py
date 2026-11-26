"""Reader-facing glossary data compiled from data/glossary.yaml (V3).

Translates the edition's curated Latin medical vocabulary, apothecary weights and symbols,
citation formulae/locators, and recurring shorthand authorities into structured sections for
/glossary/. Links authorities to /authors/<id>/ only when those pages exist in the current build.
"""

import yaml

from .. import paths
from ..layers import citations

APOTHECARY = {"℞", "℥", "ʒ", "℈", "ß", "ana", "gr."}
SYMS = ("℞", "℥", "ʒ", "℈", "ß")


def _wrap_symbols(text: str) -> list[dict]:
    """Split text into chunks tagging apothecary glyph runs for the Burton Symbols font."""
    out = []
    buf = []
    for ch in text:
        if ch in SYMS:
            if buf:
                out.append({"text": "".join(buf), "sym": False})
                buf.clear()
            out.append({"text": ch, "sym": True})
        else:
            buf.append(ch)
    if buf:
        out.append({"text": "".join(buf), "sym": False})
    return out


def _author_lookup(apages: dict) -> dict[str, str]:
    """Map abbreviated form / display name -> author page id present in `apages`."""
    if not apages:
        return {}
    by_form: dict[str, str] = {}
    t = citations.tables()
    for aid, spec in t["authors"].items():
        if aid not in apages:
            continue
        by_form[spec["name"].casefold()] = aid
        for f in spec.get("forms", []):
            by_form[f.rstrip(".").casefold()] = aid
            by_form[f.casefold()] = aid
    return by_form


def collect(apages: dict | None = None) -> dict:
    """Load data/glossary.yaml and return sections for glossary.html."""
    raw = yaml.safe_load((paths.DATA / "glossary.yaml").read_text(encoding="utf-8"))
    medical, apoth = [], []
    for item in raw.get("terms", []):
        forms = item.get("latin", [])
        row = {
            "forms": ", ".join(forms),
            "forms_parts": _wrap_symbols(", ".join(forms)),
            "render": ", ".join(item.get("render", [])),
            "note": item.get("note", ""),
        }
        if forms and forms[0] in APOTHECARY:
            apoth.append(row)
        else:
            medical.append(row)

    formulae = [{"term": k, "meaning": v} for k, v in (raw.get("formulae") or {}).items()]
    locators = [{"term": k, "meaning": v} for k, v in (raw.get("locators") or {}).items()]

    lookup = _author_lookup(apages or {})
    authorities = []
    for item in raw.get("authorities", []):
        forms = item.get("forms", [])
        name = item.get("name", "")
        aid = lookup.get(name.split(" (", 1)[0].casefold())
        if not aid:
            for f in forms:
                aid = lookup.get(f.casefold()) or lookup.get(f.rstrip(".").casefold())
                if aid:
                    break
        authorities.append({
            "forms": ", ".join(forms),
            "name": name,
            "author_id": aid,
        })

    return {
        "medical": medical,
        "apothecary": apoth,
        "formulae": formulae,
        "locators": locators,
        "authorities": authorities,
    }
