"""V11 synopsis completeness (SPEC §9): data/synopses/<pN>.json against the EPUB's hidden tables.

Independent of the builder (burton/ingest/synopses.py): it reads the XHTML and the JSON with plain lxml/json
and parses the division labels with its own pattern. Checked per partition:
* the multiset of non-glyph hidden-table strings equals the multiset of strings the tree uses (node texts, column
  headings and label paragraphs, "Or" connectors, cross-key anchors), each paragraph id exactly once, the text
  verbatim; the only duplicate allowed is the known one (nat0000108 = nat0000034a), and it must carry a reason;
* every Sect./Memb./Subsect. label in a node resolves to an existing unit inside that division;
* every `see` cross-key has exactly one node carrying that key, every keyed node is pointed to, and a key
  the image does not print is `supplied` with a reason;
* node ids are unique and active in data/ids/registry.tsv; the tree is labelled as machine-made.
"""

import csv
import json
import re
from collections import Counter

from lxml import etree

from .. import paths
from .checks import Result, norm

PARTS = {"p1": "chapter001", "p2": "chapter002", "p3": "chapter003"}
BRACES = {"⎧", "⎨", "⎩"}
KNOWN_DUPLICATES = {"nat0000108": "nat0000034a"}  # SPEC §9 V11
LABEL = re.compile(r"\b(Subsect|Sect|Memb)\.\s*(\d+(?:,\s*\d+)*)|\b(\d+)(?:st|nd|rd|th)\.?\s*(Subsect|Sect|Memb)\.")
LEADING = re.compile(r"(\d+)(?:st|nd|rd|th)?\.")
WORD = {"memb": "Memb", "subsect": "Subsect", "sect": "Sect"}


def _hidden(part: str) -> dict[str, str]:
    d = etree.parse(str(paths.XHTML / f"{PARTS[part]}.xhtml"))
    out = {}
    for table in d.iter("{*}table"):
        if "hidden_content" not in (table.get("class") or ""):
            continue
        for p in table.iter("{*}p"):
            text = "".join(p.itertext())
            if text.strip() not in BRACES:
                out[p.get("id")] = text
    return out


def _nodes(n: dict):
    for c in n.get("children", []):
        yield c
        yield from _nodes(c)


def _label_numbers(texts: list[str], num: str | None) -> list[tuple[str, int]]:
    """(label word, number) for the deepest level of each label run, in order: "Memb. 5 Sect. 2" -> [(Memb, 5)].
    `texts`: the node's text, then its heading and label paragraphs (a run never spans two of them); `num`: the
    level the structure gives the node's bare leading number."""
    out = []
    if num:
        m = LEADING.match(texts[0])
        out.append([(WORD[num], m.group(1) if m else "-1")])
    rank = {"Sect": 1, "Memb": 2, "Subsect": 3}
    for text in texts:
        last_end, run = None, []
        for m in LABEL.finditer(text):
            word, ns = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
            if run and text[last_end:m.start()].strip() == "" and word not in [w for w, _ in run]:
                run.append((word, ns))
            else:
                if run:
                    out.append(run)
                run = [(word, ns)]
            last_end = m.end()
        if run:
            out.append(run)
    nums = []
    for r in out:
        word, ns = max(r, key=lambda x: rank[x[0]])
        nums += [(word, int(n)) for n in ns.split(",")]
    return nums


def v11_synopses() -> Result:
    r = Result("V11", "synopsis completeness")
    units = {f.stem for f in paths.TEXT.glob("*.xml")}
    with (paths.DATA / "ids" / "registry.tsv").open(encoding="utf-8", newline="") as f:
        active = {row["id"] for row in csv.DictReader(f, delimiter="\t") if row["status"] == "active"}
    total = used_ok = refs = refs_ok = sees = sees_ok = nodes = 0
    for part in PARTS:
        hidden = _hidden(part)
        total += len(hidden)
        f = paths.DATA / "synopses" / f"{part}.json"
        if not f.exists():
            r.fail(f"{part}: data/synopses/{part}.json not built ({len(hidden)} strings unused)")
            continue
        tree = json.loads(f.read_text(encoding="utf-8"))
        prov = tree.get("provenance") or {}
        if prov.get("by") != "machine" or not prov.get("model") or not prov.get("date"):
            r.fail(f"{part}: tree lacks its machine label (by/model/date)")

        used: list[tuple[str, str]] = []  # (paragraph id, text as the tree carries it)
        all_nodes = list(_nodes(tree))
        nodes += len(all_nodes)
        keys = Counter(n["key"]["sign"] for n in all_nodes if "key" in n)
        for sign, k in keys.items():
            if k > 1:
                r.fail(f"{part}: {k} nodes carry cross-key {sign}")
        keyed = {n["key"]["sign"]: n for n in all_nodes if "key" in n}
        pointed = Counter()
        ids = Counter(n["id"] for n in all_nodes)
        for nid, k in ids.items():
            if k > 1:
                r.fail(f"{part}: node id {nid} used {k} times")
            if nid not in active:
                r.fail(f"{part}: node id {nid} not active in the registry")
        for n in all_nodes:
            text = "".join(run["t"] for run in n["text"])
            used.append((n["src_p"], text))
            extras = [n[k] for k in ("head", "label") if k in n]
            for x in extras:
                used.append((x["src_p"], x["text"]))
                if "".join(run["t"] for run in x["runs"]) != x["text"]:
                    r.fail(f"{part}: {n['id']} {x['src_p']} runs do not spell its text")
            if "or" in n:
                used.append((n["or"]["src_p"], n["or"]["text"]))
                if n["or"]["text"].strip().lower() != "or" or n.get("relation") != "or":
                    r.fail(f"{part}: {n['id']} connector is not an 'Or': {n['or']['text']!r}")
            if "key" in n:
                key = n["key"]
                if "src_p" in key:
                    used.append((key["src_p"], key["text"]))
                shown = key["sign"] in key.get("text", "") or key["sign"] in text
                if not shown and not key.get("supplied", "").strip():
                    r.fail(f"{part}: tree {n['id']} carries key {key['sign']} that the image does not print, "
                           "with no reason given")
            # labels
            want = _label_numbers([text] + [x["text"] for x in extras], n.get("num"))
            got = n.get("ref", [])
            refs += len(want)
            if len(got) != len(want):
                r.fail(f"{part}: {n['id']} has {len(want)} label numbers but {len(got)} refs: {text[:60]!r}")
                continue
            for (word, num), ref in zip(want, got, strict=True):
                u, div = ref.get("unit"), ref.get("div", "")
                parts = div.split(".")
                if u is None or u not in units:
                    r.fail(f"{part}: {n['id']} label {word}. {num} unresolved ({div})")
                elif not (u == div or u.startswith(div + ".")) or parts[0] != part[1:] \
                        or int(parts[-1]) != num or len(parts) != {"Sect": 2, "Memb": 3, "Subsect": 4}[word]:
                    r.fail(f"{part}: {n['id']} label {word}. {num} -> {div} / {u} does not match the label")
                else:
                    refs_ok += 1
            # cross-keys
            targets = n.get("see_target", [])
            if len(targets) != len(n.get("see", [])):
                r.fail(f"{part}: {n['id']} has {len(n.get('see', []))} cross-keys but {len(targets)} targets")
            for sign, got_t in zip(n.get("see", []), targets, strict=False):
                sees += 1
                pointed[sign] += 1
                tgt = keyed.get(sign)
                if tgt is None:
                    r.fail(f"{part}: {n['id']} points to cross-key {sign} but no tree carries it")
                elif got_t != tgt["id"]:
                    r.fail(f"{part}: {n['id']} see_target {got_t} is not the {sign} node {tgt['id']}")
                elif sign not in text:
                    r.fail(f"{part}: {n['id']} points to {sign} but its text does not show the key")
                else:
                    sees_ok += 1
        for sign, root in keyed.items():
            if not pointed[sign]:
                r.fail(f"{part}: node {root['id']} (key {sign}) is not pointed to by any node")

        # duplicates: only the known one, explained, and identical in text
        for d in tree.get("duplicates", []):
            used.append((d["src_p"], d["text"]))
            if KNOWN_DUPLICATES.get(d["src_p"]) != d.get("same_as") or not d.get("reason", "").strip():
                r.fail(f"{part}: unexplained duplicate {d['src_p']} (same_as {d.get('same_as')})")
            elif norm(hidden.get(d["src_p"], "")) != norm(hidden.get(d["same_as"], "")):
                r.fail(f"{part}: duplicate {d['src_p']} does not read the same as {d['same_as']}")

        # completeness: each id once, verbatim, and the text multisets equal
        ids_used = Counter(pid for pid, _ in used)
        for pid, k in ids_used.items():
            if k > 1:
                r.fail(f"{part}: paragraph {pid} used {k} times")
            if pid not in hidden:
                r.fail(f"{part}: paragraph {pid} is not a non-glyph hidden-table string")
        for pid in hidden.keys() - ids_used.keys():
            r.fail(f"{part}: hidden string {pid} unused: {norm(hidden[pid])[:60]!r}")
        for pid, text in used:
            if pid in hidden and text != hidden[pid]:
                r.fail(f"{part}: {pid} text differs from the EPUB: {text[:40]!r} vs {hidden[pid][:40]!r}")
        if Counter(norm(t) for _, t in used) != Counter(norm(t) for t in hidden.values()):
            r.fail(f"{part}: text multiset differs from the hidden table")
        used_ok += sum(1 for pid, t in used if hidden.get(pid) == t and ids_used[pid] == 1)
    r.counts = {"strings": f"{used_ok}/{total}", "nodes": nodes, "labels resolved": f"{refs_ok}/{refs}",
                "cross-keys linked": f"{sees_ok}/{sees}"}
    return r
