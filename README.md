# Pro. Diagrams (`pro-diagrams`)

[![CI](https://github.com/vietdq99tb/pro-diagrams/actions/workflows/ci.yml/badge.svg)](https://github.com/vietdq99tb/pro-diagrams/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-2B373E.svg)](./LICENSE)

**English** | [Tiếng Việt](./README.vi.md)

An **Agent Skill** for designing, validating, and rendering publication-grade **ISO 5807:1985 process flowcharts**, **cross-functional Swimlane SOPs & interactive Runbooks**, **topological graphs & CPM critical path networks**, **data-verified quantitative charts**, and **mathematical function plots** — running **100% on the Python 3 standard library** with zero `pip install` or desktop GUI dependencies.

Built with the **Atelier Technical Warm** palette (WCAG AA/AAA verified) and **Open Sans** typography (full Vietnamese diacritic safety).

---

## Key Capabilities

- **Smart Intake & Targeted Discovery (`references/discovery-and-elicitation.md`):** Triages prompt completeness automatically — builds immediately when a full spec is supplied, inspects attached source files first, or asks **1 concise round (2–5 high-leverage questions with recommended defaults)** when facts/numbers are missing. Never fabricates real business metrics, approval thresholds, or SLA values.
- **Track 1 — Process Flowcharts, Swimlanes & Structural Graphs (`.drawio` + `.svg` + `.html`):**
  - All **23 ISO 5807:1985 & standard flowchart symbols** (`terminator`, `process`, `decision`, `data`, `predefined_process`, `document`, `multi_document`, `database`, `direct_data`, `stored_data`, `sequential_data`, `internal_storage`, `preparation`, `manual_operation`, `manual_input`, `on_page_connector`, `off_page_connector`, `loop_limit_start`/`end`, `delay`, `display`, `parallel_mode`, `annotation`).
  - Deterministic JSON → uncompressed `.drawio` compiler (`iso5807_builder.py`) with 3-pass Sugiyama ordering, multi-lane Swimlanes (`TB` & `LR`), CPM auto-calculation (`ES/EF/LS/LF/TF`), and obstacle-free orthogonal routing (`score: 0`).
  - **11-rule ISO 5807 & WCAG AA validator** (`validate_iso5807.py`) emitting structured `diagnostics[]` + `supportedFixes[]`.
  - Pure-Python `.drawio` → standalone `.svg` / interactive `.html` viewer (`drawio_render_svg.py`, `drawiohtml.py`), step-by-step **SOP Runbook** (`runbook.py`), bilingual layout-preserving translation (`relabel.py`), lossless Light↔Dark re-theming (`restyle.py`), Mermaid export (`drawio2mermaid.py`), and 10,446-shape Draw.io search (`shapesearch.py`).
- **Track 2 — Quantitative Charts & Mathematical Function Plots (`HTML` + `SVG`):**
  - **6 quantitative chart types** (`bar`, `grouped_bar`, `horizontal_bar` with diverging negative baseline, `line`, `waterfall`, `sankey`) with KPI summary cards (`chart_builder.py`).
  - Automated **`data-*` mathematical honesty & WCAG 2.1 AA verifier** (`chart_verify.py`) checking bar/waterfall proportionality (`<= 3%`), linear line `cy` fidelity, Sankey internal-node flow conservation, and sRGB text contrast.
  - Zero-dependency AST-whitelisted **mathematical function plotter** (`plot_math_svg.py`) with singularity-safe segment splitting (`1/x`), asymptotes, shaded integral areas, and labeled extrema/roots.

---

## Visual System: Atelier Technical Warm (`Open Sans`)

| Slot | Fill (Light) | Stroke (Light) | Text Contrast | Primary Semantic Role |
|---|---|---|---|---|
| **Canvas / Surface** | `#F8F6F2` / `#FFFFFF` | `#C9D2D8` | `14.75:1` AAA | Warm Porcelain page & clean white card surfaces |
| **`neutral`** | `#FFFFFF` | `#4A5860` | `15.92:1` AAA | `Process`, `Preparation`, `Loop Limit`, `Annotation` |
| **`primary`** | `#EEF2F5` | `#2B373E` | `14.14:1` AAA | `Terminator`, `Predefined Process`, `Connector`, `Parallel Mode` |
| **`accent`** | `#FDF1EE` | `#AD4333` | `14.40:1` AAA | `Decision` diamonds, CPM Critical Path (`TF=0`), Focal KPI |
| **`secondary`** | `#EDF3F6` | `#395E73` | `14.22:1` AAA | `Data I/O`, `Database`, Storage symbols, `Display` |
| **`warning`** | `#FAF4EA` | `#8C5D2B` | `14.55:1` AAA | `Document`, `Manual Operation`, `Manual Input`, `Delay` |
| **`danger`** | `#FCECEB` | `#9E2F2C` | `13.90:1` AAA | Critical error / exception termination |
| **`success`** | `#EEF4F1` | `#2D6A5B` | `14.29:1` AAA | Restrained positive `+Δ` chart indicators |

Includes matching dark mode (`tech-warm-dark`), accessible Okabe-Ito (`colorblind-safe`), and sketch (`handdrawn`) presets.

---

## Installation

### Universal Agent Skills CLI (Claude Code, Cursor, Codex, Antigravity, Copilot, OpenCode)

```bash
npx skills add vietdq99tb/pro-diagrams
```

### Manual Installation

```bash
git clone https://github.com/vietdq99tb/pro-diagrams.git
cp -r pro-diagrams/skills/pro-diagrams ~/.claude/skills/pro-diagrams
# Or for project-local / Codex / Cursor / Antigravity:
# cp -r pro-diagrams/skills/pro-diagrams .agents/skills/pro-diagrams
```

See [`skills/pro-diagrams/INSTALL_GUIDE.md`](skills/pro-diagrams/INSTALL_GUIDE.md) for Vietnamese setup and CLI recipes.

---

## Quick CLI Usage & Testing

```bash
# Run all 26 unit & adversarial regression tests (Python 3 stdlib only)
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s skills/pro-diagrams/tests -v

# Compile ISO 5807 flowchart / swimlane -> .drawio + .svg + interactive .html + SOP Runbook
python3 skills/pro-diagrams/scripts/iso5807_builder.py spec.json \
  -o flow.drawio \
  --render-svg flow.svg \
  --render-html flow.html \
  --render-runbook flow_runbook.html

# Validate strictly against ISO 5807:1985 + WCAG AA rules
python3 skills/pro-diagrams/scripts/validate_iso5807.py flow.drawio --strict --score

# Build & verify a data-* honest quantitative chart
python3 skills/pro-diagrams/scripts/chart_builder.py chart_spec.json -o chart.html --svg chart.svg
python3 skills/pro-diagrams/scripts/chart_verify.py chart.html

# Plot mathematical functions y = f(x) to standalone SVG/HTML
python3 skills/pro-diagrams/scripts/plot_math_svg.py math_spec.json -o plot.svg --html plot.html
```

---

## Repository Layout

```text
pro-diagrams/
├── README.md
├── LICENSE
├── .github/workflows/ci.yml
└── skills/pro-diagrams/
    ├── SKILL.md                  # Main router (progressive disclosure)
    ├── INSTALL_GUIDE.md          # Vietnamese installation & CLI guide
    ├── LICENSE                   # MIT + Third-Party Notices
    ├── data/                     # ISO 5807 catalog, theme tokens, 10,446 Draw.io shape index
    ├── references/               # 7 focused reference docs (incl. discovery-and-elicitation.md)
    ├── scripts/                  # 20 zero-dependency Python 3 stdlib scripts
    ├── styles/                   # JSON schema + 4 built-in presets
    ├── evals/                    # Benchmark prompt suite
    └── tests/                    # 26 comprehensive unit & adversarial tests
```

---

## License & Attributions

Released under the **MIT License** ([`LICENSE`](./LICENSE)).
Built upon the modular `.drawio` core of [`Agents365-ai/drawio-skill`](https://github.com/Agents365-ai/drawio-skill) (MIT), incorporating Apache-2.0 Draw.io shape index metadata (`jgraph/drawio-mcp`, see `skills/pro-diagrams/data/SHAPE-INDEX-NOTICE.md`), conceptual `data-*` chart honesty verification inspired by [`cathrynlavery/diagram-design`](https://github.com/cathrynlavery/diagram-design) (MIT), and structured `diagnostics[]`/`supportedFixes[]` linter contracts inspired by [`tt-a1i/archify`](https://github.com/tt-a1i/archify) (Apache-2.0).
