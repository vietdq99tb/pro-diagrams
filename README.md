# Pro. Diagrams (`pro-diagrams`)

[![CI](https://github.com/vietdq99tb/pro-diagrams/actions/workflows/ci.yml/badge.svg)](https://github.com/vietdq99tb/pro-diagrams/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-2B373E.svg)](./LICENSE)

**English** | [Tiếng Việt](./README.vi.md)

An **Agent Skill** for designing, validating, and rendering publication-grade **ISO 5807:1985 process flowcharts**, **ISO 5807 cross-functional Swimlane SOPs & interactive Runbooks**, **topological graphs & CPM critical path networks**, **data-verified quantitative charts**, and **mathematical function plots** — running **100% on the Python 3 standard library** with zero `pip install` or desktop GUI dependencies.

Built with the **Atelier Technical Warm** palette (WCAG AA/AAA verified) and **Open Sans** typography (full Vietnamese diacritic safety).

---

## Key Capabilities

- **Smart Intake & Targeted Discovery (`references/discovery-and-elicitation.md`):** Triages prompt completeness automatically — builds immediately when a full spec is supplied, inspects attached source files first, or asks **1 concise round (2–5 high-leverage questions with recommended defaults)** when facts/numbers are missing. Never fabricates real business metrics, approval thresholds, or SLA values.
- **Track 1 — ISO 5807:1985 Diagrams (§4–§11), Cross-Functional Swimlanes & Structural Graphs (`.drawio` + `.svg` + `.html`):**
  - **All 5 ISO 5807:1985 chart types (§4–§8) verified against official Annex A–E:** `data-flowchart` (§4, Annex A), `program-flowchart` / `iso5807-flowchart` (§5, Annex B(a)/B(b)), `system-flowchart` (§6, Annex C), `program-network` (§7, Annex D), and `system-resources` (§8, Annex E) — plus **ISO 5807 cross-functional Swimlanes** and **CPM / DAG networks**.
  - **26 node symbols + 4 ISO §9.3 line types (`data/iso5807-shapes.json`):** 24 ISO 5807:1985 symbols (including `card` §9.1.2.6, `paper_tape` §9.1.2.7, `ellipsis` §9.4.4, and §10.3.2 stacked `multi_document` per-layer `"items": [...]`) + 2 explicitly marked extensions (`delay`, `off_page_connector`); bidirectional read/write lines (`startArrow` + `endArrow` in `.drawio` & `.svg`), Control Transfer `P`/`T`/`I` triangles (§9.3.2.1), Communication Link zigzags (§9.3.2.2), and single-stem Decision fan-outs (§10.3.1(b)).
  - **Strict upfront JSON schema & DAG validation (`iso5807_builder.py`):** Rejects typos in node `type`, dangling edge `from`/`to`, unknown `lane`/`slot`/`attach_to`, and post-trim duplicate whitespace lane IDs. Runs CPM only when `kind == "cpm"` or `"compute_cpm": true` (so SOP `duration` fields never trigger false CPM errors, while circular CPM networks still abort cleanly).
  - **Diagram-type-aware ISO 5807 validator (`validate_iso5807.py`):** Rejects blank/chrome-only pages (`E-ISO-EMPTY`), checks single-entrance Decisions (`E-ISO-DECISION-ENTRY` §9.2.2.4), treats `>3`-exit Decisions as advisory layout hints (`I-LAYOUT-DECISION-FANOUT`), verifies Loop Limit start–end pairs per `loop_id` (`E-ISO-LOOP-PAIR` §9.2.2.6), pairs cross-page connectors & page references across `<diagram>` pages (§9.4.1 / §10.2.2), and separates `iso_compliant` from layout/WCAG contrast warnings (`--diagram-type`, `--iso-only`).
  - Pure-Python `.drawio` → standalone `.svg` / interactive `.html` viewer (`drawio_render_svg.py`, `drawiohtml.py`) verified with strict `.drawio` ↔ `.svg` parity, step-by-step **SOP Runbook** (`runbook.py`), bilingual layout-preserving translation (`relabel.py`), lossless Light↔Dark re-theming (`restyle.py`), Mermaid export (`drawio2mermaid.py`), and 10,446-shape Draw.io search (`shapesearch.py`).
- **Track 2 — Quantitative Charts & Mathematical Function Plots (`HTML` + `SVG`):**
  - **6 quantitative chart types** (`bar`, `grouped_bar`, `horizontal_bar` with diverging negative baseline, `line`, `waterfall`, `sankey`) with KPI summary cards (`chart_builder.py`).
  - Automated **`data-*` mathematical honesty & WCAG 2.1 AA verifier** (`chart_verify.py`) checking bar/waterfall proportionality (`<= 3%`), linear line `cy` fidelity, Sankey internal-node flow conservation, and sRGB text contrast.
  - Zero-dependency AST-whitelisted **mathematical function plotter** (`plot_math_svg.py`) with singularity-safe segment splitting (`1/x`), asymptotes, shaded integral areas, and labeled extrema/roots.

---

## Visual System: Atelier Technical Warm (`Open Sans`)

| Slot | Fill (Light) | Stroke (Light) | Text Contrast | Primary Semantic Role |
|---|---|---|---|---|
| **Canvas / Surface** | `#F8F6F2` / `#FFFFFF` | `#C9D2D8` | `14.75:1` AAA | Warm Porcelain page & clean white card surfaces |
| **`neutral`** | `#FFFFFF` | `#4A5860` | `15.92:1` AAA | `Process`, `Preparation`, `Loop Limit`, `Annotation`, `Ellipsis` |
| **`primary`** | `#EEF2F5` | `#2B373E` | `14.14:1` AAA | `Terminator`, `Predefined Process`, `Connector`, `Parallel Mode` |
| **`accent`** | `#FDF1EE` | `#AD4333` | `14.40:1` AAA | `Decision` diamonds, CPM Critical Path (`TF=0`), Focal KPI |
| **`secondary`** | `#EDF3F6` | `#395E73` | `14.22:1` AAA | `Data I/O`, `Database`, Storage, `Card`, `Paper Tape`, `Display` |
| **`warning`** | `#FAF4EA` | `#8C5D2B` | `14.55:1` AAA | `Document`, `Manual Operation`, `Manual Input`, `Delay` |
| **`danger`** | `#FCECEB` | `#9E2F2C` | `13.90:1` AAA | Critical error / exception termination |
| **`success`** | `#EEF4F1` | `#2D6A5B` | `14.29:1` AAA | Restrained positive `+Δ` chart indicators |

Includes matching dark mode (`tech-warm-dark`), accessible Okabe-Ito (`colorblind-safe`), and sketch (`handdrawn`) presets.

---

## Ready-to-Run Examples (`examples/`)

Every example below includes the input `spec.json` plus pre-rendered, strictly validated outputs (CI regenerates and diffs every committed file byte-for-byte):

| Example | Track | Input Spec | Verified Outputs |
|---|---|---|---|
| **Payment Retry & E-Invoice Flowchart** | ISO 5807:1985 (`TB`, retry loop + `A→A` connector) | [`spec.json`](examples/iso5807-payment-retry/spec.json) | [`.drawio`](examples/iso5807-payment-retry/payment_retry.drawio) · [`.svg`](examples/iso5807-payment-retry/payment_retry.svg) · [`.html`](examples/iso5807-payment-retry/payment_retry.html) (`0 err, 0 warn, score: 0`) |
| **4-Lane R&D Procurement SOP** | ISO 5807 Cross-Functional Swimlane + Runbook | [`spec.json`](examples/swimlane-rd-procurement/spec.json) | [`.drawio`](examples/swimlane-rd-procurement/procurement.drawio) · [`.svg`](examples/swimlane-rd-procurement/procurement.svg) · [`.html`](examples/swimlane-rd-procurement/procurement.html) · [`_runbook.html`](examples/swimlane-rd-procurement/procurement_runbook.html) (`0 err, 0 warn, score: 0`) |
| **2026 OpEx Variance Waterfall** | Quantitative Chart (`850 → 860 tr`, `data-*` verified) | [`spec.json`](examples/waterfall-opex-2026/spec.json) | [`.html`](examples/waterfall-opex-2026/waterfall_opex_2026.html) · [`.svg`](examples/waterfall-opex-2026/waterfall_opex_2026.svg) (`6 data-* marks PASS`) |

---

## Installation

### Universal Agent Skills CLI (Claude Code, Cursor, Codex, Antigravity, Copilot, OpenCode)

```bash
npx skills add vietdq99tb/pro-diagrams
```

### Manual Installation / Offline `.skill` Archive

```bash
git clone https://github.com/vietdq99tb/pro-diagrams.git
cp -r pro-diagrams/skills/pro-diagrams ~/.claude/skills/pro-diagrams
# Or for project-local / Codex / Cursor / Antigravity:
# cp -r pro-diagrams/skills/pro-diagrams .agents/skills/pro-diagrams
```

For Claude Desktop, Windows PowerShell, or offline ZIP import, download `pro-diagrams.skill` from [GitHub Releases](https://github.com/vietdq99tb/pro-diagrams/releases) (Windows PowerShell: `Copy-Item pro-diagrams.skill pro-diagrams.zip; Expand-Archive pro-diagrams.zip -DestinationPath "$env:USERPROFILE\.claude\skills" -Force`). See [`skills/pro-diagrams/INSTALL_GUIDE.md`](skills/pro-diagrams/INSTALL_GUIDE.md) for full Vietnamese setup and CLI recipes.

---

## Quick Start & Testing

Run directly from a fresh clone using the bundled examples:

```bash
# 1. Run all 38 unit, adversarial & ISO 5807:1985 Annex A-E regression tests (Python 3 stdlib only)
PYTHONDONTWRITEBYTECODE=1 python3 -B -W error::ResourceWarning -m unittest discover -s skills/pro-diagrams/tests -v

# 2. Compile the 4-lane ISO 5807 Swimlane SOP -> .drawio + .svg + interactive .html + SOP Runbook
python3 skills/pro-diagrams/scripts/iso5807_builder.py \
  examples/swimlane-rd-procurement/spec.json \
  -o /tmp/procurement.drawio \
  --render-svg /tmp/procurement.svg \
  --render-html /tmp/procurement.html \
  --render-runbook /tmp/procurement_runbook.html

# 3. Validate strictly against ISO 5807:1985 (§4–§11), Swimlane & WCAG AA rules
python3 skills/pro-diagrams/scripts/validate_iso5807.py /tmp/procurement.drawio --strict --score

# 4. Build & verify the 2026 OpEx Waterfall chart (data-* mathematical honesty)
python3 skills/pro-diagrams/scripts/chart_builder.py \
  examples/waterfall-opex-2026/spec.json \
  -o /tmp/waterfall.html --svg /tmp/waterfall.svg
python3 skills/pro-diagrams/scripts/chart_verify.py /tmp/waterfall.html
```

---

## Repository Layout

```text
pro-diagrams/
├── README.md
├── README.vi.md
├── LICENSE
├── .github/workflows/
│   ├── ci.yml                    # Linux Python 3.11/3.12 (38 tests + examples/ diff) & Windows PowerShell .skill test
│   └── release.yml               # Automated GitHub Release packaging pro-diagrams.skill on v* tags
├── examples/
│   ├── iso5807-payment-retry/    # Runnable ISO 5807 flowchart (spec.json + .drawio + .svg + .html)
│   ├── swimlane-rd-procurement/  # Runnable 4-lane ISO 5807 Swimlane SOP + interactive Runbook
│   └── waterfall-opex-2026/      # Runnable data-* verified Waterfall chart (.html + .svg)
└── skills/pro-diagrams/
    ├── SKILL.md                  # Main router (progressive disclosure)
    ├── INSTALL_GUIDE.md          # Vietnamese installation & CLI guide
    ├── LICENSE                   # MIT + Third-Party Notices
    ├── data/                     # ISO 5807 §4–§11 catalog (26 symbols + 4 lines), theme tokens, Draw.io index + APACHE-2.0.txt
    ├── references/               # 7 focused reference docs (incl. discovery-and-elicitation.md)
    ├── scripts/                  # 20 zero-dependency Python 3 stdlib scripts
    ├── styles/                   # JSON schema + 4 built-in presets
    ├── evals/                    # Benchmark prompt suite
    └── tests/                    # 38 comprehensive unit, adversarial & Annex A–E regression tests
```

---

## License & Attributions

Released under the **MIT License** ([`LICENSE`](./LICENSE)).
Built upon the modular `.drawio` core of [`Agents365-ai/drawio-skill`](https://github.com/Agents365-ai/drawio-skill) (MIT), incorporating Apache-2.0 Draw.io shape index metadata (`jgraph/drawio-mcp`, full verbatim license text bundled at [`skills/pro-diagrams/data/APACHE-2.0.txt`](skills/pro-diagrams/data/APACHE-2.0.txt) per Apache-2.0 §4(a), attribution at [`skills/pro-diagrams/data/SHAPE-INDEX-NOTICE.md`](skills/pro-diagrams/data/SHAPE-INDEX-NOTICE.md)), conceptual `data-*` chart honesty verification inspired by [`cathrynlavery/diagram-design`](https://github.com/cathrynlavery/diagram-design) (MIT), and structured `diagnostics[]`/`supportedFixes[]` linter contracts inspired by [`tt-a1i/archify`](https://github.com/tt-a1i/archify) (Apache-2.0).
