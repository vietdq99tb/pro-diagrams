---
name: pro-diagrams
description: Design, build, validate, and render publication-grade ISO 5807:1985 process flowcharts, ISO 5807 cross-functional swimlane SOPs, topological graphs (DAGs, trees, dependency networks, state machines, CPM critical path diagrams), quantitative statistical charts (bar, grouped bar, line, waterfall, sankey, KPI comparisons), and mathematical function plots using the Atelier Technical Warm palette, Open Sans typography, and WCAG AA contrast. Make sure to use this skill whenever the user asks to draw a flowchart, sơ đồ quy trình, lưu đồ thuật toán, chuẩn ISO 5807, swimlane liên phòng ban, SOP runbook, đồ thị cấu trúc, mạng đường găng CPM, đồ thị hàm số, biểu đồ số liệu/thống kê, or wants editable .drawio plus standalone SVG/HTML previews — even if they do not explicitly mention ISO 5807 or draw.io. Do not use when the user explicitly asks for a quick inline Mermaid snippet only (e.g., "vẽ nhanh bằng Mermaid") or wants a brand logo/icon (use logo-design).
---

# Pro. Diagrams (`pro-diagrams`)

Create deterministic, geometrically verified, visually refined diagrams and charts across two specialized tracks so every output is **100% editable where needed**, **previewable anywhere with zero external binary dependencies**, and **mathematically faithful to standards and data**.

---

## 1. Smart Intake & Targeted Discovery (Hỏi & Khai Thác Thông Tin Trước Khi Vẽ)

Before writing a spec or drawing, evaluate whether the prompt already contains enough real facts to build an accurate diagram/chart — **never fabricate real business numbers, approval thresholds, SLA durations, or mathematical formulas**, and **never interrogate users who already supplied a complete specification**:

- **Build immediately (skip questions)** when the user already specifies concrete steps + decision outcomes (flowcharts/swimlanes), tasks + predecessors/durations (CPM/DAG), actual data values + units (charts), or exact equations + domain (math plots) — OR explicitly asks for a sample/proposed draft (*"vẽ mẫu"*, *"tự đề xuất quy trình chuẩn"*). State any minor formatting defaults at the end.
- **Inspect attached sources first** (code, CSV/JSON, SOP docs, existing `.drawio`) and extract everything available before asking only about genuine gaps.
- **Ask 1 concise discovery round (2–5 high-leverage questions max)** when critical domain facts, exception paths, chart takeaway, or real numbers are missing or ambiguous. Read `references/discovery-and-elicitation.md` to choose the right diagram/chart type and pull targeted questions for that track. Batch all questions into a single turn (prefer structured multiple-choice options with `(Khuyến nghị)` defaults via `ask_question` when available, or a numbered list so the user can reply *"dùng mặc định"*).

---

## 2. Route the Request (Dual-Track Architecture)

In Vietnamese and technical communication, *"sơ đồ"* and *"đồ thị"* span distinct visual domains. Identify the matching track below and read **only** the referenced guide(s) before generating files:

| User Intent | Track | Read Reference(s) | Primary Script Pipeline (`scripts/`) | Deliverables |
|---|---|---|---|---|
| **Vague / Underspecified Diagram or Chart Goal** | `discovery` | `references/discovery-and-elicitation.md` | 1-round targeted clarification (2–5 questions + chart-type recommendation) → proceed to matching track below | Confirmed spec / brief |
| **Process / Algorithm Flowchart (ISO 5807:1985)** | `iso5807-flowchart` | `references/iso-5807-standard.md`, `references/theme-atelier-tech-warm.md` | `iso5807_builder.py` → `validate_iso5807.py --strict --score` | `.drawio` + `.svg` + `.html` viewer |
| **ISO 5807 Cross-Functional Swimlane SOP** | `swimlane-sop` | `references/swimlane-and-sop.md`, `references/iso-5807-standard.md`, `references/theme-atelier-tech-warm.md` | `iso5807_builder.py` → `validate_iso5807.py --strict --score` → **mandatory** `--render-runbook` / `runbook.py` whenever user requests SOP runbook / interactive walkthrough | `.drawio` + `.svg` + `.html` + `_runbook.html` |
| **Topological / Network Graph & CPM Critical Path** | `topological-graph` | `references/topological-graphs.md`, `references/theme-atelier-tech-warm.md` | `iso5807_builder.py` (`kind: "topological-graph"` or `"cpm"`) → `validate.py --score` | `.drawio` + `.svg` + `.html` |
| **Quantitative / Statistical / KPI Chart** | `quantitative-chart` | `references/quantitative-and-math-charts.md`, `references/theme-atelier-tech-warm.md` | `chart_builder.py` → `chart_verify.py` | Self-contained `.html` + PowerPoint-ready `.svg` |
| **Mathematical Function Plot (`y = f(x)`)** | `math-plot` | `references/quantitative-and-math-charts.md`, `references/theme-atelier-tech-warm.md` | `plot_math_svg.py` | `.svg` + `.html` |
| **Edit Raw `.drawio`, Translate VI↔EN, Re-theme, Search 10k+ Shapes** | `repurpose` | `references/xml-routing-and-qa.md`, `references/swimlane-and-sop.md` | `shapesearch.py`, `edgeports.py`, `relabel.py`, `restyle.py`, `drawio_render_svg.py`, `drawio2mermaid.py`, `encode_drawio_url.py` | Updated `.drawio` + `.svg` / `.html` / `.mmd` |

All script paths below are relative to this skill's directory (`<skill-dir>/scripts/...`). Every core script runs on **Python 3 standard library only** — no `pip install` or desktop GUI app is required.

---

## 3. Visual Identity & Typography Contract (`Atelier Technical Warm` + `Open Sans`)

Unless the user explicitly requests dark mode (`--preset tech-warm-dark` / `--theme tech-warm-dark`) or supplies another custom JSON preset, apply the **`tech-warm-light`** system (`references/theme-atelier-tech-warm.md`):

- **Design philosophy (*Kim tạo cấu trúc · Hỏa tạo dấu ấn · Thổ tạo độ ấm*):**
  - **Warm Porcelain canvas (`#F8F6F2`) & Crisp White surfaces (`#FFFFFF`)** (~48% visual area) eliminate industrial coldness while keeping print and slides clean.
  - **Structural Slate (`#2B373E`), Titanium (`#4A5860`), and Obsidian Ink (`#1C2327`)** (~36% combined structure + technical neutrals) provide disciplined ISO framing and **13.9:1–15.9:1 (WCAG AAA)** text legibility.
  - **Kiln Terracotta (`#AD4333` stroke / `#FDF1EE` fill)** (~10% focal budget) is reserved purposefully for `Decision` diamonds, CPM Critical Paths (`TF = 0`), exception branches, and focal KPI series — never neon orange or traffic-light green/red clutter.
  - **Mineral Water (`#395E73` / `#EDF3F6`) & Burnished Sand (`#8C5D2B` / `#FAF4EA`)** (~6% warm/flow accents) distinguish `Data I/O` + `Database` vs `Document` + `Manual` symbols at a glance. Do **not** use green as a primary brand or default Start/Process color.
- **Typography (`Open Sans`):**
  - Always use `'Open Sans', 'Segoe UI', Roboto, Arial, sans-serif` (`JetBrains Mono` for numeric axes, metrics, and formulas).
  - Respect stacked Vietnamese diacritics (`ệ, ổ, ữ, ắ, ẫ`): keep node heights `>= 60px` (`>= 76px` for 3 lines), `line-height >= 1.4`, concise verb-first node labels, and edge labels `<= 18` characters with opaque label backgrounds (`#F8F6F2`).

---

## 4. Core Execution Loop (Compile → Validate → Render → Self-Fix `<= 2` Rounds)

### Track 1: Flowcharts (ISO 5807), Swimlanes & Structural Graphs (`.drawio` + `.svg` + `.html`)

Why use the JSON compiler instead of hand-guessing coordinates first? Hand-written coordinates frequently clip Vietnamese text, omit decision labels, or route edges across sibling boxes. `iso5807_builder.py` computes topological ranks, barycenter ordering, Swimlane coordinates, CPM slack, and orthogonal outer-corridor loop waypoints deterministically, while outputting standard uncompressed `.drawio` XML that opens cleanly in diagrams.net / VS Code.

1. **Author the JSON spec** following `references/iso-5807-standard.md` (or `swimlane-and-sop.md` / `topological-graphs.md`). Map every step to its exact ISO 5807 symbol (all 23 keys: `terminator`, `process`, `decision`, `data`, `predefined_process`, `document`, `multi_document`, `database`, `direct_data`, `stored_data`, `sequential_data`, `internal_storage`, `preparation`, `manual_operation`, `manual_input`, `on_page_connector`, `off_page_connector`, `loop_limit_start`, `loop_limit_end`, `delay`, `display`, `parallel_mode`, `annotation`).
2. **Compile `.drawio` AND standalone `.svg` + `.html` previews in one step — `--render-runbook` is MANDATORY whenever the user asks for an interactive SOP runbook or step-by-step walkthrough (`"hướng dẫn vận hành tương tác"` / `"runbook"`):**
   ```bash
   python3 <skill-dir>/scripts/iso5807_builder.py spec.json \
     -o diagram.drawio \
     --render-svg diagram.svg \
     --render-html diagram.html \
     --render-runbook diagram_runbook.html   # required for SOP runbook / walkthrough requests
   ```
   *(If `drawio` desktop CLI is also installed on the host and raster PNG/PDF with embedded XML is requested, locate the binary via `drawio_cli.py`, export with `drawio -x -f png -e -o diagram.drawio.png diagram.drawio`, and run `repair_png.py diagram.drawio.png`; otherwise `drawio_render_svg.py` also supports `--png diagram.png` via headless Chrome when available.)*
3. **Run the deterministic validator:**
   - For ISO 5807 flowcharts & swimlanes:
     ```bash
     python3 <skill-dir>/scripts/validate_iso5807.py diagram.drawio --strict --score
     ```
   - For general DAG / Tree / CPM topological graphs:
     ```bash
     python3 <skill-dir>/scripts/validate.py diagram.drawio --score
     ```
4. **Self-fix if needed (`<= 2` rounds):** If any `E-*` or `W-*` finding appears, run with `--json` to inspect `supportedFixes[]`, update the JSON spec (or run `edgeports.py` if editing XML directly), and re-render until `0 error(s)`.

### Track 2: Quantitative Charts & Mathematical Function Plots

Never eyeball bar heights, waterfall steps, or curve coordinates in raw SVG — LLMs routinely distort proportions.

- **Quantitative / KPI Charts:** Write a JSON spec (`bar`, `grouped_bar`, `horizontal_bar`, `line`, `waterfall`, or `sankey`) and run:
  ```bash
  python3 <skill-dir>/scripts/chart_builder.py chart_spec.json -o chart.html --svg chart.svg
  python3 <skill-dir>/scripts/chart_verify.py chart.html
  ```
  `chart_verify.py` verifies `data-*` proportional geometry (`<= 3%` tolerance on bars, horizontal bars, waterfall steps, and linear line `cy`), Waterfall step conservation, Sankey internal-node flow conservation, WCAG 2.1 AA text contrast, valid `viewBox`, and UTF-8 integrity.
- **Mathematical Function Plots (`y = f(x)`):** Write a JSON function spec (expressions, domain/range, asymptotes, shaded area, extrema/root points) and run:
  ```bash
  python3 <skill-dir>/scripts/plot_math_svg.py math_spec.json -o plot.svg --html plot.html
  ```

---

## 5. Presenting Outputs to the User

- Always deliver **both** the editable source artifact (`.drawio` for Track 1; `.html` with `data-*` for Track 2) **and** the standalone vector `.svg` (ready for PowerPoint, Word, Markdown, or web preview).
- When running in an interactive UI that supports HTML artifacts or previews, surface the generated `.html` viewer so the user can pan, zoom, search nodes, or step through an interactive SOP Runbook (`runbook.py`) immediately.
