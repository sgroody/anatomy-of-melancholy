"""Layered, Stage-Aware Human-UX, Design-Principles & Burton-Elucidation Workflow.

Zero-freeze design:
  - Deterministic OS helpers (audit_human_ux.py, prepare_packets.py, workbench_renderer.py) run via
    `uv run python` against C:\\Users\\Grood\\Melancholy.
  - Child agents (`type_name="research"`, no shell/write tools) receive 100% of their evidence inline
    and call `finish` immediately without external file or command calls.
  - Supports running stage-by-stage (`Args={"stage": "layer1"|"layer2"|"layer3"|"layer4"|"layer5"|"all"}`)
    so the orchestrator can print plain-English live progress updates after each layer.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

REPO = Path("C:/Users/Grood/Melancholy")
AUDIT_JSON = REPO / "state" / "review" / "human-ux-audit-2026-11-25.json"
PERSONAS_JSON = REPO / "state" / "review" / "human-ux-personas-2026-11-25.json"
SYNTHESIS_JSON = REPO / "state" / "review" / "human-ux-synthesis-2026-11-25.json"
SYNTHESIS_MD = REPO / "state" / "review" / "human-ux-synthesis-2026-11-25.md"
CUSTOM_DEMOS_JSON = REPO / "state" / "review" / "_ux_custom_demos.json"
WORKBENCH_HTML = REPO / "state" / "review" / "human-ux-2026-11-25.html"
SHOTS_DIR = REPO / "state" / "review" / "ux-shots-2026-11-25"

wf_args = globals().get("args") or {}
STAGE = str(wf_args.get("stage", "all")).lower()

ws_list = globals().get("WORKSPACES") or ()
ws0 = Path(ws_list[0]) if ws_list else REPO
if ws0.resolve() != REPO.resolve():
    STAGE_DIR = ws0 / "_melancholy_ux_stage"
else:
    STAGE_DIR = REPO / "state" / "review" / "_ux_stage"
PACKETS_DIR = STAGE_DIR / "packets"


def run_repo_py(rel_script: str, *extra_args: str) -> str:
    proc = subprocess.run(
        ["uv", "run", "python", rel_script, *extra_args],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return proc.stdout.strip()


def load_guardrail_digest() -> str:
    claude_lines = (REPO / "CLAUDE.md").read_text(encoding="utf-8").splitlines()[:66]
    to_revisit = (REPO / "state" / "review" / "to-revisit.md").read_text(encoding="utf-8").strip()
    return f"""## Non-Negotiable Edition Rules (CLAUDE.md lines 1-66)
{chr(10).join(claude_lines)}

## Open Provisional Items to Revisit (state/review/to-revisit.md)
{to_revisit}

## Settled Rounds 1-9 Owner Aesthetic & Functional Choices
- Strict Non-Destructive Scope: Never alter base text ('data/text/*.xml'), never invent attributions, label machine work with '◇' on reading pages, NEVER show '◇' on the front page ('home.html' + 'front_key.html'), zero Gowland leaks in public builds, 100% static/offline PWA.
- Front Page ('home.html'): One screen with no running header/footer and no scrollbars before opening Synopses or Contents; frontispiece title magnifies on hover; Democritus Abderites stanza shown first; live interactive specimen in '+ How a page looks'; Synopses folded between rubric rules with '⁂' expand-all; Contents folded by default.
- Typography & Colour: EB Garamond (Greek in GFS Didot, Chaucer in small-caps); Latin oxblood ('#7a2230') by day & candle-gold ('#e0c27a') by night.
- Margins & Notes: Two-sided margins from 1380 px (Gowland left, Burton notes + translations right, crossing over cleanly); long notes shortened with 'more' (never held back); filled red box for Burton's note letters & rubric rule beside his words; quiet 'g' / 'dj' / 'w' / 'kjv' / 'dm' / '◇' source marks.
- Navigation & Modes: '☙' / '❧' side-edge page turners on wide pointer screens; top-left '{{' synopsis path mark; 'As printed' leaf button hiding all added colours/notes/translations while keeping Burton's own text and sidenotes pure.
"""


def count_section_items(md_text: str, heading: str) -> int:
    m = re.search(rf"(?ims)^###\s*{re.escape(heading)}.*?(?=^###\s|\Z)", md_text)
    if not m:
        return 3
    sec = m.group(0)
    bracket_hits = re.findall(r"(?m)^\s*(?:[-*]|\d+\.)?\s*\[[^\]]+\]", sec)
    if bracket_hits:
        return len(bracket_hits)
    bullet_hits = re.findall(r"(?m)^\s*(?:[-*]|\d+\.)\s+", sec)
    return len(bullet_hits) if bullet_hits else 3


# ============================================================================
# LAYER 1: Empirical Sensor & Workspace Packet Staging
# ============================================================================
if STAGE in ("layer1", "all"):
    phase("Layer 1: Empirical Sensor, Elucidation Audit & Mirror Staging")
    if not AUDIT_JSON.exists() or wf_args.get("rerun_sensor"):
        log("Running headless Playwright, marginalia drift & elucidation sensor (audit_human_ux.py)...")
        out = run_repo_py("tools/human_ux_workflow/audit_human_ux.py")
        log(out)
    else:
        log(f"Loaded cached Layer 1 audit: {AUDIT_JSON}")

    stage_out = run_repo_py("tools/human_ux_workflow/prepare_packets.py", "--stage-dir", str(STAGE_DIR))
    log(stage_out)

    sensor_data = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    fp_vp = sensor_data["browser_probes"]["front_page_viewports"]
    failing_one_screen = [
        f"{k} (+{v['overflowY']}px)" for k, v in fp_vp.items() if v["w"] >= 1100 and not v["fitsOneScreen"]
    ]
    eluc = sensor_data.get("elucidation_coverage", {})
    drift = sensor_data.get("browser_probes", {}).get("margin_density_and_drift_3_2_3_1", {})
    scroll_ret = sensor_data.get("browser_probes", {}).get("mode_switch_scroll_retention_3_2_3_1", {})
    log(f"1100px+ viewports wrapping off 1 screen: {failing_one_screen}")
    log(f"Elucidation counts: {json.dumps(eluc, ensure_ascii=False)}")
    log(f"Margin drift (3.2.3.1): {json.dumps(drift, ensure_ascii=False)}")
    log(f"Mode-switch scroll retention (3.2.3.1-p60): {json.dumps(scroll_ret, ensure_ascii=False)}")


# ============================================================================
# LAYER 2: 6 Parallel Human-Persona & Burton-Elucidation Passes (Flash Tier)
# ============================================================================
if STAGE in ("layer2", "all"):
    phase("Layer 2: 6 Parallel Human-Persona & Elucidation Field Trials (Flash Tier)")
    if PERSONAS_JSON.exists() and not wf_args.get("rerun_personas"):
        persona_reports = json.loads(PERSONAS_JSON.read_text(encoding="utf-8"))
        log(f"Loaded cached Layer 2 personas: {PERSONAS_JSON}")
    else:
        if not PACKETS_DIR.exists() or not (PACKETS_DIR / "persona_1.md").exists():
            run_repo_py("tools/human_ux_workflow/prepare_packets.py", "--stage-dir", str(STAGE_DIR))
        sensor_data = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
        guardrail = load_guardrail_digest()

        compact_sensor = {
            "corpus_and_navigation": sensor_data.get("corpus_and_navigation"),
            "elucidation_coverage": sensor_data.get("elucidation_coverage"),
            "browser_probes": {
                k: v for k, v in sensor_data.get("browser_probes", {}).items() if k != "front_page_viewports"
            },
            "front_page_failing_1100plus": {
                k: v for k, v in sensor_data.get("browser_probes", {}).get("front_page_viewports", {}).items()
                if not v.get("fitsOneScreen")
            },
        }
        compact_sensor_json = json.dumps(compact_sensor, indent=2, ensure_ascii=False)

        PERSONAS = [
            {
                "role": "Persona 1: First-Time Cultural Visitor",
                "name": "First-Time Cultural Visitor",
                "packet": PACKETS_DIR / "persona_1.md",
                "focus": (
                    "Evaluate the first 10 minutes of a curious newcomer:\n"
                    "1. Why 1440x900 and 1280x800 16:10 laptops wrap to 1 column and push Synopses/Contents off-screen.\n"
                    "2. Touch frontispiece behavior ('a.fs-panel' navigating away instead of previewing the stanza first).\n"
                    "3. Front-page 'Aa' Reading Options lacking '.opt-sample' preview and Reset button.\n"
                    "4. Orienting newcomers from 'Enter, gentle Reader' through 'djr' (64,162 words!) without cluttering the 1-screen front page."
                ),
            },
            {
                "role": "Persona 2: Sustained Night & Mobile Reader",
                "name": "Sustained Night, Commute & Mobile/Tablet Reader",
                "packet": PACKETS_DIR / "persona_2.md",
                "focus": (
                    "Evaluate sustained multi-week reading on laptop/dark/half-screen/iPad/phone:\n"
                    "1. Mode-switch & size-switch scroll safety ('apply()' calling 'scheduleLayout()' without explicit paragraph scroll-anchoring across browsers/type sizes).\n"
                    "2. Missing session place-keeping across 44 units > 5,000 words and 64,162-word 'djr'.\n"
                    "3. Sub-1100px touch parity gaps: '.ic-m' ('§') unfocusable & dead on tap, 252/253 Gowland notes invisible without cue below 1100 px, 'a.nm' navigating away immediately on tap instead of previewing."
                ),
            },
            {
                "role": "Persona 3: Early Modern Scholar & Student",
                "name": "Early Modern Scholar, Philologist & Seminar Student",
                "packet": PACKETS_DIR / "persona_3.md",
                "focus": (
                    "Evaluate scholarly research, cross-edition citation, and deep linking:\n"
                    "1. Deep-link arrival failure ('/3.2.3.1/#3.2.3.1-n5'): 'layoutNotes()' moves notes off-screen & unlit; 'search.js' does not highlight matched terms on arrival.\n"
                    "2. Scholarly citation copier ('#3.2.3.1-p35' + 'Part. Sect. Memb. Subsect. [p. 714]') and direct jump to Penguin page numbers ('p. 412', '3.2.3.1').\n"
                    "3. Research index friction on 'Authors cited' (253 rows, no citation sort/alias filter) and 'The Table' (574 entries, no A-Z bar or filter)."
                ),
            },
            {
                "role": "Persona 4: Dipper & Commonplacer",
                "name": "Browsing Dipper, Bibliomancer & Commonplacer",
                "packet": PACKETS_DIR / "persona_4.md",
                "focus": (
                    "Evaluate serendipitous dipping, curiosity trails, and personal reading notebooks:\n"
                    "1. Period-authentic, zero-server Personal Commonplace Book in 'localStorage' with Markdown export & full Burton citations.\n"
                    "2. Curated doorways into Burton's great set-pieces (Digression of Air, Misery of Scholars, Nature of Spirits, Love-Melancholy, Remedies for Discontents) + Sortes Burtonianae.\n"
                    "3. Turning 'data/glossary.yaml' into a reader-facing Humoral & Technical Terms Glossary ('/glossary/', already sketched in 'SPEC.md')."
                ),
            },
            {
                "role": "Persona 5: Burton Elucidation & Design Critic",
                "name": "Burton Elucidation & Human Design-Principles Critic",
                "packet": PACKETS_DIR / "persona_5.md",
                "focus": (
                    "Evaluate how well the UI applies human-centered design principles (progressive disclosure, cognitive-load control, clear visual hierarchy, forgiving exploration) specifically to elucidate Burton:\n"
                    "1. Dense margin overload & vertical drift (measured on '3.2.3.1': 811 margin cards, 85 drifting >120 px at 1440 px, 217 folding on 1120 px). How can readers navigate crowded margins without feeling overwhelmed?\n"
                    "2. Burton's own self-translations ('.burton-tr', 3,435 across the book): how can we let readers notice Burton's witty free paraphrases vs literal translations ('g' / 'dj' / '◇') without clutter?\n"
                    "3. Untapped elucidation assets (935 obsolete glosses off by default, 1,181 restored Democritus Minor notes off by default, 'data/glossary.yaml' Galenic/humoral & apothecary 'ß' signs, and Burton's own 2,367 substantive marginalia signposts)."
                ),
            },
            {
                "role": "Persona 6: Book Typographer & Craft Critic",
                "name": "Book Typographer & Interaction Craftsmanship Critic",
                "packet": PACKETS_DIR / "persona_6.md",
                "focus": (
                    "Evaluate print craft, subtle CSS/JS bugs, keyboard ergonomics, and the two 'to-revisit.md' items:\n"
                    "1. '@media print' at >= 1380px: '.two-side .unit' leaves non-zero 'margin-left' when '@media print' only sets 'margin: 0' then 'margin-right: 31% !important'.\n"
                    "2. '.mn-fold.hot > .fold-more' ('edition.css:1126') fades to 'var(--paper)' instead of blending with gold '--hot' highlight.\n"
                    "3. Keyboard navigation ('/', 'Esc', '['/']' or arrow turning, keyboard focusability of '.pw' author/xref windows).\n"
                    "4. Thoughtful assessment of 'state/review/to-revisit.md' items 'P3' (left-margin rubric rule inner vs outer edge) and 'H2' (synopsis hover-rest pace)."
                ),
            },
        ]

        def build_scout_prompt(p: dict) -> str:
            packet_text = p["packet"].read_text(encoding="utf-8")
            return f"""You are {p['name']} evaluating the digital edition of Robert Burton's *Anatomy of Melancholy*.

CRITICAL EXECUTION RULES:
- DO NOT call read_file, grep_search, find_by_name, or ANY tool other than finish. 100% of the code, CSS, JS, and Playwright evidence you need is embedded below. Call finish immediately on your first turn.
- Never create, edit, or delete any file. Ground every finding in exact line numbers, selectors, and measured counts from the packet below.
- Keep your output as a clean, concise 350-550 word Markdown report passed to `finish` under these exact three headings, using plain prose and single quotes (no fenced code blocks, no HTML angle brackets):
### Shines
- (2-3 bullets on what already works wonderfully and must not be broken)
### Friction Findings
- [ID] Title (severity) — Where: exact file/lines — Evidence: measured count/behavior — Remedy: concise fix
### Unconsidered Visions
- [ID] Title — Human value — Burtonian fit — Sketch: how it works quietly

{guardrail}

## Layer 1 Empirical Measurements
```json
{compact_sensor_json}
```

## Your Assigned Evidence Packet
{packet_text}

## Your Assignment
{p['focus']}

Call `finish` immediately with that structured Markdown string."""

        async def run_scout(p: dict) -> dict:
            prompt = build_scout_prompt(p)
            try:
                md_text = await agent(
                    prompt,
                    schema={"type": "string"},
                    role=p["role"],
                    type_name="research",
                    workspace="inherit",
                    model="flash",
                )
            except Exception as err:
                log(f"Flash scout fallback to Pro for {p['name']} after error: {err}")
                md_text = await agent(
                    prompt,
                    schema={"type": "string"},
                    role=f"{p['role']} (Pro retry)",
                    type_name="research",
                    workspace="inherit",
                    model="pro",
                )
            return {
                "persona": p["name"],
                "role": p["role"],
                "friction_count": count_section_items(md_text, "Friction Findings"),
                "vision_count": count_section_items(md_text, "Unconsidered Visions"),
                "report_markdown": md_text.strip(),
            }

        persona_reports = await parallel(PERSONAS, run_scout)
        PERSONAS_JSON.write_text(json.dumps(persona_reports, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        log(f"Saved Layer 2 persona reports to {PERSONAS_JSON}")

    for rep in persona_reports:
        fc = rep.get("friction_count", len(rep.get("friction_findings", [])))
        vc = rep.get("vision_count", len(rep.get("unconsidered_visions", [])))
        log(f"{rep['persona']}: {fc} friction findings, {vc} visions")


# ============================================================================
# LAYER 3: Carbon Guardrail Judge & Editorial Taste Synthesis (Pro Tier)
# ============================================================================
SYNTHESIS_SCHEMA = {
    "type": "object",
    "required": [
        "executive_verdict",
        "preserved_strengths",
        "tier1_silent_fixes",
        "tier2_reading_ergonomics",
        "tier3_unconsidered_visions",
        "revisit_items_assessment",
        "vetoed_or_quarantined",
    ],
    "properties": {
        "executive_verdict": {"type": "string"},
        "preserved_strengths": {"type": "array", "items": {"type": "string"}},
        "tier1_silent_fixes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["code", "title", "problem", "evidence", "remedy", "files_touched_if_adopted", "risk"],
                "properties": {
                    "code": {"type": "string"},
                    "title": {"type": "string"},
                    "problem": {"type": "string"},
                    "evidence": {"type": "string"},
                    "remedy": {"type": "string"},
                    "files_touched_if_adopted": {"type": "array", "items": {"type": "string"}},
                    "risk": {"type": "string"},
                },
            },
        },
        "tier2_reading_ergonomics": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["code", "title", "human_need", "design_proposal", "variants_to_ab", "guardrail_check"],
                "properties": {
                    "code": {"type": "string"},
                    "title": {"type": "string"},
                    "human_need": {"type": "string"},
                    "design_proposal": {"type": "string"},
                    "variants_to_ab": {"type": "array", "items": {"type": "string"}},
                    "guardrail_check": {"type": "string"},
                },
            },
        },
        "tier3_unconsidered_visions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["code", "title", "vision", "why_burtonian", "how_it_stays_quiet", "implementation_shape"],
                "properties": {
                    "code": {"type": "string"},
                    "title": {"type": "string"},
                    "vision": {"type": "string"},
                    "why_burtonian": {"type": "string"},
                    "how_it_stays_quiet": {"type": "string"},
                    "implementation_shape": {"type": "string"},
                },
            },
        },
        "revisit_items_assessment": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["code", "title", "current_choice", "recommendation", "options"],
                "properties": {
                    "code": {"type": "string"},
                    "title": {"type": "string"},
                    "current_choice": {"type": "string"},
                    "recommendation": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "vetoed_or_quarantined": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["idea", "why_vetoed"],
                "properties": {
                    "idea": {"type": "string"},
                    "why_vetoed": {"type": "string"},
                },
            },
        },
    },
}

if STAGE in ("layer3", "all"):
    phase("Layer 3: Carbon Guardrail Judge & Editorial Taste Synthesis (Pro)")
    if SYNTHESIS_JSON.exists() and not wf_args.get("rerun_synthesis"):
        synthesis = json.loads(SYNTHESIS_JSON.read_text(encoding="utf-8"))
        log(f"Loaded cached Layer 3 synthesis: {SYNTHESIS_JSON}")
    else:
        sensor_data = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
        persona_reports = json.loads(PERSONAS_JSON.read_text(encoding="utf-8"))
        guardrail = load_guardrail_digest()

        synth_prompt = f"""You are the Lead Orchestrator & Constitutional Guardrail Judge (Carbon / Pro tier) for Burton's *Anatomy of Melancholy*.

CRITICAL RULES:
- DO NOT call read_file, grep_search, find_by_name, or ANY tool other than finish. All evidence is provided inline below. Immediately synthesize and return structured JSON via `finish`.
- Inside JSON string values, write clean plain English without raw HTML tags, backticks, or unescaped double quotes (use single quotes like '.front-side' when naming selectors/files).
- Keep descriptions lucid for a non-coder owner while preserving exact file names/selectors in 'evidence' and 'files_touched_if_adopted'.

{guardrail}

## Layer 1 Empirical Measurements
```json
{json.dumps(sensor_data, indent=2, ensure_ascii=False)}
```

## Layer 2 Persona & Elucidation Field Trials (6 scouts)
```json
{json.dumps(persona_reports, indent=2, ensure_ascii=False)}
```

Your Mandate:
1. VETO & QUARANTINE any idea that violates CLAUDE.md (base text edits, invented attributions, hiding '◇' on reading pages, adding '◇' to the front page, Gowland leaks in public builds, server requirements) OR reverses Rounds 1-9 taste (floating clutter over text, cluttering the 1-screen front page, always-on scrollbars, cluttering 'As printed', replacing EB Garamond / oxblood / candle-gold). Record explicit rejections in 'vetoed_or_quarantined'.
2. SYNTHESIZE & DEDUPLICATE surviving proposals cleanly:
   - 'tier1_silent_fixes' (F1..F5, up to 5 crisp fixes): High-confidence viewport, deep-link, <1100px touch parity, and CSS/print bugs.
   - 'tier2_reading_ergonomics' (E1..E5, up to 5 items): Scroll-anchoring safety across mode/size toggles, quiet reading-place memory, scholarly locus/citation copier + Penguin page jumper, Authors Cited & The Table finder/sort, keyboard accessibility for '.pw' & page turns.
   - 'tier3_unconsidered_visions' (V1..V6, up to 6 visions): Quiet, Burtonian breakthroughs — Personal Commonplace Book (localStorage), Ways into the Labyrinth + Sortes Burtonianae, reader-facing Humoral & Technical Glossary ('/glossary/'), Burton's self-translation & gloss lens, Long-Unit Marginalia Signpost Compass, calm margin density relief.
   - 'revisit_items_assessment' (P3, H2): Sharp plain-English comparison for the two items in 'to-revisit.md'."""

        try:
            synthesis = await agent(
                synth_prompt,
                schema=SYNTHESIS_SCHEMA,
                role="Carbon Guardrail Judge (Pro)",
                type_name="research",
                workspace="inherit",
                model="pro",
            )
        except Exception as err:
            log(f"Retrying Layer 3 Carbon synthesis once after error: {err}")
            synthesis = await agent(
                synth_prompt + "\n\nKeep each string concise (1-2 sentences) so JSON serialization succeeds cleanly.",
                schema=SYNTHESIS_SCHEMA,
                role="Carbon Guardrail Judge (Pro retry)",
                type_name="research",
                workspace="inherit",
                model="pro",
            )
        SYNTHESIS_JSON.write_text(json.dumps(synthesis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md = [
        "# Human-Centered UX Synthesis & Guardrail Docket (2026-11-25)",
        "",
        f"> **Executive Verdict:** {synthesis['executive_verdict']}",
        "",
        "## What Shines (Preserved Untouched)",
        *[f"- {s}" for s in synthesis["preserved_strengths"]],
        "",
        "## Tier 1 · Silent Craftsmanship, Viewport & Parity Fixes",
    ]
    for f in synthesis["tier1_silent_fixes"]:
        md += [
            f"### {f['code']} — {f['title']} (`{f['risk']}` risk)",
            f"- **Human problem:** {f['problem']}",
            f"- **Measured evidence:** {f['evidence']}",
            f"- **Remedy:** {f['remedy']}",
            f"- **Files if adopted:** {', '.join(f'`{x}`' for x in f['files_touched_if_adopted'])}",
            "",
        ]
    md.append("## Tier 2 · Intuitive Reading & Scholarly Ergonomics")
    for e in synthesis["tier2_reading_ergonomics"]:
        md += [
            f"### {e['code']} — {e['title']}",
            f"- **Human need:** {e['human_need']}",
            f"- **Design:** {e['design_proposal']}",
            f"- **A/B choices:** {' · '.join(e['variants_to_ab'])}",
            f"- **Guardrail check:** {e['guardrail_check']}",
            "",
        ]
    md.append("## Tier 3 · Elucidating Burton & Unconsidered Visions")
    for v in synthesis["tier3_unconsidered_visions"]:
        md += [
            f"### {v['code']} — {v['title']}",
            f"- **Vision:** {v['vision']}",
            f"- **Why Burtonian:** {v['why_burtonian']}",
            f"- **How it stays quiet:** {v['how_it_stays_quiet']}",
            f"- **Implementation shape:** {v['implementation_shape']}",
            "",
        ]
    md.append("## Open Revisit Items (`state/review/to-revisit.md`)")
    for r in synthesis["revisit_items_assessment"]:
        md += [
            f"### {r['code']} — {r['title']}",
            f"- **Current:** {r['current_choice']}",
            f"- **Recommendation:** {r['recommendation']}",
            f"- **Options:** {' · '.join(r['options'])}",
            "",
        ]
    md.append("## Guardrail Veto Log (Ideas Deliberately Rejected)")
    for q in synthesis["vetoed_or_quarantined"]:
        md.append(f"- **{q['idea']}** — *Vetoed:* {q['why_vetoed']}")
    SYNTHESIS_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    log(
        f"Saved synthesis ({len(synthesis['tier1_silent_fixes'])} T1, "
        f"{len(synthesis['tier2_reading_ergonomics'])} T2, "
        f"{len(synthesis['tier3_unconsidered_visions'])} T3, "
        f"{len(synthesis['vetoed_or_quarantined'])} vetoed) -> {SYNTHESIS_MD}"
    )


# ============================================================================
# LAYER 4: Interactive Owner's Workbench Builder (Carbon Polish + Renderer)
# ============================================================================
CURATOR_SCHEMA = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["code", "prototype_key", "why_it_matters"],
                "properties": {
                    "code": {"type": "string"},
                    "prototype_key": {
                        "type": "string",
                        "enum": [
                            "front_16_10", "touch_parity", "deep_link_drift", "polish_fixes",
                            "scroll_bookmark", "cite_jumper", "authors_table_finder",
                            "elucidation_lens", "glossary_live", "commonplace_book",
                            "sortes_labyrinth", "discourse_compass", "revisit_p3", "revisit_h2",
                        ],
                    },
                    "why_it_matters": {"type": "string"},
                },
            },
        }
    },
}

if STAGE in ("layer4", "all"):
    phase("Layer 4: Interactive Owner's Workbench Builder")
    synthesis = json.loads(SYNTHESIS_JSON.read_text(encoding="utf-8"))
    curator_prompt = f"""You are curating the interactive UX Workbench for the owner of Burton's *Anatomy of Melancholy*.
DO NOT call read_file, grep_search, find_by_name, or ANY tool other than finish.
Inside JSON string values, write clean plain English without raw HTML tags, backticks, or unescaped double quotes (use single quotes when needed).
Review every item code in the synthesis JSON below and return via `finish` a mapping entry for EVERY item code ('tier1_silent_fixes', 'tier2_reading_ergonomics', 'tier3_unconsidered_visions', 'revisit_items_assessment'):
- 'prototype_key': choose the best matching built-in interactive demo key from the enum;
- 'why_it_matters': one crisp, plain-English sentence (no developer jargon) explaining what changes for a real human reader.

```json
{json.dumps(synthesis, indent=2, ensure_ascii=False)}
```"""
    try:
        curator_out = await agent(
            curator_prompt,
            schema=CURATOR_SCHEMA,
            role="Workbench Prototype Curator (Pro)",
            type_name="research",
            workspace="inherit",
            model="pro",
        )
    except Exception as err:
        log(f"Retrying Layer 4 curator once after error: {err}")
        curator_out = await agent(
            curator_prompt + "\n\nKeep each 'why_it_matters' under 25 words.",
            schema=CURATOR_SCHEMA,
            role="Workbench Prototype Curator (Pro retry)",
            type_name="research",
            workspace="inherit",
            model="pro",
        )
    custom_map = {x["code"]: x for x in curator_out.get("items", [])}
    CUSTOM_DEMOS_JSON.write_text(json.dumps(custom_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        render_out = run_repo_py("tools/human_ux_workflow/workbench_renderer.py")
        log(render_out)
    finally:
        if CUSTOM_DEMOS_JSON.exists():
            CUSTOM_DEMOS_JSON.unlink()


# ============================================================================
# LAYER 5: Deterministic Integrity & Browser Gate
# ============================================================================
if STAGE in ("layer5", "all"):
    phase("Layer 5: Deterministic Playwright & Repo Integrity Gate")
    VERIFY_SCRIPT = r"""
import json, pathlib, subprocess
from burton.verify.browser import browser, new_page, serve

repo = pathlib.Path(r"C:\Users\Grood\Melancholy")
shots = repo / "state" / "review" / "ux-shots-2026-11-25"
shots.mkdir(parents=True, exist_ok=True)

git_out = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(repo), text=True, encoding="utf-8")
dirty_tracked = [ln for ln in git_out.splitlines() if ln.strip() and not ln.startswith("?? ")]

py_res = subprocess.run(["uv", "run", "pytest", "-q"], cwd=str(repo), capture_output=True, text=True, encoding="utf-8")

errs = []
checks = {}
with serve(repo) as (_, base), browser() as b:
    for mode, w, h, shot_name in [
        ("light", 1440, 900, "workbench_light.png"),
        ("dark", 1440, 900, "workbench_dark.png"),
        ("light", 390, 844, "workbench_mobile.png"),
    ]:
        ctx, pg = new_page(b, width=w, height=h, theme=mode)
        pg.on("pageerror", lambda e: errs.append(f"{mode}@{w}: pageerror: {e}"))
        pg.on("console", lambda m: errs.append(f"{mode}@{w}: console.{m.type}: {m.text}") if m.type == "error" else None)
        pg.on("dialog", lambda d: errs.append(f"{mode}@{w}: unexpected dialog: {d.message}") or d.dismiss())
        pg.goto(base + "state/review/human-ux-2026-11-25.html", wait_until="load")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(200)
        if mode == "dark":
            pg.click("#themeBtn")
            pg.wait_for_timeout(100)
        ov = pg.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        items = pg.locator(".item").count()
        if w == 1440 and mode == "light":
            pg.click("#acceptTier1")
            pg.click("#copyBtn")
            pg.wait_for_timeout(100)
            checks["tally_after_accept"] = pg.locator("#tally").text_content()
            checks["copy_msg"] = pg.locator("#copiedMsg").text_content()
            pg.click("#resetPicks")
        checks[f"{mode}_{w}"] = {"overflowX": ov, "items": items}
        if shot_name:
            pg.screenshot(path=str(shots / shot_name))
        ctx.close()

out = {
    "dirty_tracked_count": len(dirty_tracked),
    "dirty_tracked": dirty_tracked,
    "pytest_returncode": py_res.returncode,
    "pytest_tail": py_res.stdout.strip().splitlines()[-1] if py_res.stdout.strip() else "",
    "console_errors_count": len(errs),
    "console_errors": errs,
    "checks": checks,
}
print(json.dumps(out, ensure_ascii=False))
"""
    proc = subprocess.run(
        ["uv", "run", "python", "-c", VERIFY_SCRIPT],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        verify_report = {"passed": False, "error": proc.stderr or proc.stdout}
    else:
        raw = json.loads(proc.stdout.strip().splitlines()[-1])
        issues = []
        if raw["dirty_tracked_count"] > 0:
            issues.append(f"Tracked files modified: {raw['dirty_tracked']}")
        if raw["pytest_returncode"] != 0:
            issues.append(f"pytest failed: {raw['pytest_tail']}")
        if raw["console_errors_count"] > 0:
            issues.append(f"Browser console errors: {raw['console_errors']}")
        for k, v in raw["checks"].items():
            if isinstance(v, dict):
                if v["overflowX"] > 0:
                    issues.append(f"Horizontal overflow at {k}: {v['overflowX']}px")
                if v["items"] < 10:
                    issues.append(f"Too few workbench items at {k}: {v['items']}")
        verify_report = {"passed": len(issues) == 0, "issues": issues, **raw}

    log(f"Verification gate: passed={verify_report.get('passed')}, issues={verify_report.get('issues')}")
    if ws0.resolve() != REPO.resolve() and STAGE_DIR.exists():
        shutil.rmtree(STAGE_DIR, ignore_errors=True)
        log(f"Cleaned temporary staging directory: {STAGE_DIR}")
    verify_report
