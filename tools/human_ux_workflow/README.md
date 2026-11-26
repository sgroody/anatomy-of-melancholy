# Layered Human-Centered UX Workflow (`tools/human_ux_workflow/`)

A non-destructive, five-layer agentic evaluation and prototyping pipeline for *The Anatomy of Melancholy* reader (`site/private`), built to work cleanly whether launched inside `C:\Users\Grood\Melancholy` or from a mobile/scratch T3 Code thread.

## Architecture

| Layer | Role | Model / Runner | Output |
|---|---|---|---|
| **Layer 1 — Empirical Sensor & Packet Staging** | Runs headless Playwright across 11 viewports (`1920×1080` down to `390×844`), touch parity, deep-link arrivals (`#note`, `#pg-N`, `#pN`), dense-margin drift (`3.2.3.1`), mode-switch scroll retention, and elucidation coverage across all 159 units; mirrors read-only packets inside the active workspace so child agents never block on out-of-workspace reads. | Deterministic Python (`audit_human_ux.py`, `prepare_packets.py`) | `state/review/human-ux-audit-2026-11-25.json` + screenshots |
| **Layer 2 — Parallel Human-Persona & Elucidation Trials** | 6 concurrent read-only reader & design passes (*First-Time Visitor*, *Sustained Night & Mobile Reader*, *Early Modern Scholar*, *Dipper & Commonplacer*, *Burton Elucidation & Design Principles*, *Book Typographer & Revisit Craft*). | `parallel(..., model="flash")` | `state/review/human-ux-personas-2026-11-25.json` |
| **Layer 3 — Carbon Guardrail Judge & Synthesis** | Cross-examines all 6 scout reports against `CLAUDE.md` and Rounds 1–9 owner preferences; vetoes bloat or provenance violations; synthesizes Tiers 1–3 + `P3`/`H2`. | `agent(..., model="pro")` | `state/review/human-ux-synthesis-2026-11-25.json` & `.md` |
| **Layer 4 — Interactive Owner's Workbench Builder** | Curates plain-English rationales (`model="pro"`) and renders the offline-resilient workbench with live interactive prototypes, `localStorage` pickers, and a Guardrail Veto Log (`workbench_renderer.py`). | `agent(..., model="pro")` + Python | `state/review/human-ux-2026-11-25.html` |
| **Layer 5 — Deterministic Integrity & Browser Gate** | Verifies `git status --porcelain` (`0` tracked modifications), `uv run pytest -q` (`159 passed`), and headless Chromium across `1440×900` (light/dark) and `390×844` (`0` console errors, `0` overflow). | Deterministic Python + Playwright | Screenshots + verified counts |

## Running

- **T3 Code button:** Click **UX Workbench & Review Pages** in the project's top script bar to open `http://127.0.0.1:8790/state/review/human-ux-2026-11-25.html`.
- **Stage-by-stage or full run:** Execute `tools/human_ux_workflow/workflow.py` via `run_workflow` with `Cwd: C:\Users\Grood\Melancholy` and `Args: {"stage": "layer1"|"layer2"|"layer3"|"layer4"|"layer5"|"all"}`.
