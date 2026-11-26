"""The frontispiece with clickable panels (M8): each panel of the engraving links to the stanza of
"The Argument of the Frontispiece" that describes it, and each stanza links back to its panel.

The panels' rectangles are a machine reading of the image (data/manual/frontispiece.yaml, labelled
with its provenance); the stanza numbers and words come from the base text.
"""

import re
from functools import cache

import yaml
from lxml import etree

from .. import paths
from ..tei import XML_ID, T, public_id
from ..textview import public_text
from .render import attr, esc, prov


@cache
def load() -> dict:
    return yaml.safe_load((paths.MANUAL / "frontispiece.yaml").read_text(encoding="utf-8"))


@cache
def stanza_numbers() -> dict[str, str]:
    """Verse group id -> the stanza number Burton prints at its head ("2", "8 9")."""
    root = etree.parse(str(paths.TEXT / "argument.xml")).getroot()
    out = {}
    for lg in root.iter(T("lg")):
        m = re.match(r"(\d+(?: \d+)*) ", public_text(lg))
        if m and lg.get(XML_ID):
            out[public_id(lg.get(XML_ID))] = m.group(1)
    return out


def label() -> str:
    p = load()["provenance"]
    return f"Panels outlined from the engraving by machine ({p['model']}, {p['date']}), {p['status'].replace('-', ' ')}"


def figure_html(src: str, alt: str, w: int, h: int, argument_href: str, *, here: bool,
                caption: str | None = "", zoom_title: bool = False) -> str:
    """The engraving with one link per panel. `argument_href` is the Argument page ("" when this is
    it). `here` gives each panel an id, so a stanza can link back to it. `caption` (HTML) opens the
    figure's caption, with the machine's label for the panels' outlines; None leaves the caption out (the front page:
    owner, 2026-11-21, "no diamond at all on the front page, it's clutter"; the label stands on the Argument page,
    where the panels lead, and in About). `zoom_title` adds a zone over the title panel, which the script magnifies
    within the engraving's bounds while the pointer rests on it (the front page, owner 2026-11-21)."""
    data = load()
    nums = stanza_numbers()
    W, H = data["size"]
    if (w, h) != (W, H):
        raise SystemExit(f"frontispiece.yaml is for a {W}x{H} image, {data['image']} is {w}x{h}")
    links = []
    for pn in data["panels"]:
        x, y, pw, ph = pn["rect"]
        st = pn["stanza"]
        if st not in nums:
            raise SystemExit(f"frontispiece.yaml: {st} is not a numbered stanza of the Argument")
        style = (f"left:{100 * x / W:.2f}%;top:{100 * y / H:.2f}%;"
                 f"width:{100 * pw / W:.2f}%;height:{100 * ph / H:.2f}%")
        pid = f' id="panel-{pn["n"]}"' if here else ""
        name = f"Panel {pn['n']}, {pn['name']}: stanza {nums[st]} of the Argument"
        links.append(f'<a class="fs-panel"{pid} href="{attr(argument_href)}#{attr(st)}" data-st="{attr(st)}" '
                     f'style="{style}" '
                     f'aria-label="{attr(name)}"><span class="fs-n" aria-hidden="true">{pn["n"]}</span></a>')
    zone, zvars = "", ""
    if zoom_title and data.get("title"):
        x, y, tw, th = data["title"]
        s = min(1.72, W / tw, H / th)  # gentle 1.72x loupe without snapping too hard
        cx, cy = 100 * (x + tw / 2) / W, 100 * (y + th / 2) / H
        zvars = f' style="--zx:{cx:.2f}%;--zy:{cy:.2f}%;--zs:{s:.3f}"'
        zone = (f'<span class="fs-title" aria-hidden="true" style="left:{100 * x / W:.2f}%;top:{100 * y / H:.2f}%;'
                f'width:{100 * tw / W:.2f}%;height:{100 * th / H:.2f}%"></span>')
    cap = "" if caption is None else f'<figcaption class="fs-label">{caption} {prov(label())}</figcaption>'
    return (f'<div class="fs-map"{zvars}><img src="{attr(src)}" alt="{attr(alt)}" width="{w}" height="{h}" '
            f'decoding="async">{zone}{"".join(links)}</div>{cap}')


def glosses_from(page_html: str) -> dict[str, list[tuple[int, str, str, str]]]:
    """The margin items of the rendered Argument page that hang on a word of a described stanza (Gowland's glosses,
    private build): stanza id -> [(line index, the word, the item's id, the item's HTML)]. Taken from the page as
    the reader shows it, so the front page shows the same items, labelled the same (owner, 2026-11-21: "with the
    same hovering/tapping functionality as in the reader")."""
    if not page_html:
        return {}
    from copy import deepcopy

    from lxml import html as lhtml
    tree = lhtml.fromstring(page_html)
    wanted = {pn["stanza"] for pn in load()["panels"]}
    out: dict[str, list] = {}
    for sid in wanted:
        lg = tree.xpath(f'//div[@id="{sid}"]')
        if not lg:
            continue
        lines = lg[0].xpath('./span[contains(concat(" ", @class, " "), " l ")]')
        for i, line in enumerate(lines):
            for mref in line.xpath('.//span[contains(@class, "mref")]'):
                item = tree.xpath(f'//*[@id="{mref.get("data-for")}"]')
                if not item:
                    continue
                probe = deepcopy(line)  # where the anchor stands in the line's text: a sentinel in its place
                for m in probe.xpath('.//span[contains(@class, "mref")]'):
                    m.tail = ("\ue000" if m.get("data-for") == mref.get("data-for") else "") + (m.tail or "")
                    m.drop_tree()
                text = probe.text_content()
                k = text.find("\ue000")
                word = text[k + 1:k + 1 + int(mref.get("data-len") or 0)]
                note = deepcopy(item[0])
                nid = "fs-" + note.get("id")
                note.set("id", nid)
                note.set("class", (note.get("class") or "") + " fs-mn")
                for a_ in note.xpath(".//a[@href]"):  # the Argument page is one level down
                    if a_.get("href").startswith("../"):
                        a_.set("href", a_.get("href")[3:])
                if word.strip():
                    out.setdefault(sid, []).append((i, word, nid, lhtml.tostring(note, encoding="unicode")))
    return out


def stanzas_html(glosses: dict | None = None, hint: str = "") -> str:
    """Each described stanza of the Argument, Burton's lines as the base text has them, for the front page: one
    shows at a time under the way in, as the reader points at a panel (owner, 2026-11-03: T14, R4 B), the first
    (Democritus Abderites, old Democritus under his tree) shown to begin with (owner, 2026-11-21). When `glosses`
    is None (AB-2 B), sets the verse full-width without side margin notes and places `hint` gently beside the
    first stanza's heading."""
    root = etree.parse(str(paths.TEXT / "argument.xml")).getroot()
    names = {pn["stanza"]: [] for pn in load()["panels"]}
    for pn in load()["panels"]:
        names[pn["stanza"]].append(pn["name"])
    out = []
    for lg in root.iter(T("lg")):
        sid = public_id(lg.get(XML_ID)) if lg.get(XML_ID) else ""
        if sid not in names:
            continue
        lines = [esc(" ".join(public_text(ln).split())) for ln in lg.iter(T("l"))]
        if lines:  # the stanza number Burton prints, said by the heading instead
            lines[0] = re.sub(r"^\d+(?: \d+)* ", "", lines[0])
        hidden = " hidden" if out else ""
        if glosses is None:
            eyebrow = f'<span class="fs-st-hint"> · {esc(hint)}</span>' if (not out and hint) else ""
            out.append(f'<div class="fs-st" data-st="{attr(sid)}"{hidden}><div class="fs-st-main">'
                       f'<p class="fs-st-h">{esc(" and ".join(names[sid]))}{eyebrow}</p>'
                       f'<p class="fs-st-l">{"<br>".join(lines)}</p></div></div>')
            continue
        side = []
        for i, word, nid, note in glosses.get(sid, []):
            w = esc(word)
            if i < len(lines) and w in lines[i]:
                lines[i] = lines[i].replace(w, f'<span class="fs-anc" data-for="{attr(nid)}">{w}</span>', 1)
                side.append(note)
        if not out and hint:
            side.insert(0, hint)
        out.append(f'<div class="fs-st" data-st="{attr(sid)}"{hidden}><div class="fs-st-main"><p class="fs-st-h">'
                   f'{esc(" and ".join(names[sid]))}</p>'
                   f'<p class="fs-st-l">{"<br>".join(lines)}</p></div>'
                   f'<div class="fs-st-side">{"".join(side)}</div></div>')
    return "".join(out)


def back_links() -> dict[str, list[tuple[int, str]]]:
    """Stanza id -> [(panel number, panel name)], for the links from each stanza to its panel."""
    out: dict[str, list] = {}
    for pn in load()["panels"]:
        out.setdefault(pn["stanza"], []).append((pn["n"], pn["name"]))
    return out


def add_back_links(body: str) -> tuple[str, int]:
    """On the Argument page: a link at the head of each described stanza to its panel."""
    n = 0
    for st, panels in back_links().items():
        links = " ".join(f'<a href="#panel-{k}">panel {k}, {esc(name)}</a>' for k, name in panels)
        tag = f'<div class="lg" id="{st}">'
        if tag not in body:
            raise SystemExit(f"frontispiece.yaml: stanza {st} not found on the Argument page")
        body = body.replace(tag, f'{tag}<p class="to-panel">In the engraving: {links}</p>', 1)
        n += len(panels)
    return body, n
