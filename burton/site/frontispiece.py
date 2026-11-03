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
from .render import attr, esc


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


def figure_html(src: str, alt: str, w: int, h: int, argument_href: str, *, here: bool, caption: str = "") -> str:
    """The engraving with one link per panel. `argument_href` is the Argument page ("" when this is
    it). `here` gives each panel an id, so a stanza can link back to it. `caption` (HTML) opens the
    figure's caption."""
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
        links.append(f'<a class="fs-panel"{pid} href="{attr(argument_href)}#{attr(st)}" style="{style}" '
                     f'aria-label="{attr(name)}"><span class="fs-n" aria-hidden="true">{pn["n"]}</span></a>')
    return (f'<div class="fs-map"><img src="{attr(src)}" alt="{attr(alt)}" width="{w}" height="{h}" '
            f'decoding="async">{"".join(links)}</div>'
            f'<figcaption class="fs-label">{caption}{esc(label())}. Choose a panel to read its stanza.</figcaption>')


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
