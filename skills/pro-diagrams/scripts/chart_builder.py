#!/usr/bin/env python3
"""Deterministic HTML+SVG Quantitative Chart Builder with `data-*` Honesty Attributes.

Supports:
  - chart_type: "bar" | "grouped_bar" | "horizontal_bar" | "line" | "waterfall" | "sankey"
  - Optional KPI summary cards (`kpis: [{"label": "...", "value": "...", "delta": "..."}]`)
  - Theme: "tech-warm-light" (default) | "tech-warm-dark"
  - Typography: Open Sans + JetBrains Mono (tabular numerals), WCAG AA/AAA contrast

Usage:
  python3 chart_builder.py chart_spec.json -o chart.html [--svg chart.svg]
"""
import argparse
import html
import json
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)


def _load_theme(theme_name):
    with open(os.path.join(SKILL_DIR, "data", "theme-tokens.json"), encoding="utf-8") as f:
        data = json.load(f)
    return data["themes"].get(theme_name, data["themes"]["tech-warm-light"])


def _nice_ticks(vmin, vmax, count=5):
    if abs(vmax - vmin) < 1e-9:
        vmax = vmin + 1.0
    span = vmax - vmin
    raw_step = span / max(1, count)
    mag = 10 ** math.floor(math.log10(raw_step))
    norm = raw_step / mag
    if norm <= 1:
        step = 1 * mag
    elif norm <= 2:
        step = 2 * mag
    elif norm <= 2.5:
        step = 2.5 * mag
    elif norm <= 5:
        step = 5 * mag
    else:
        step = 10 * mag
    lo = math.floor(vmin / step) * step
    hi = math.ceil(vmax / step) * step
    ticks = []
    cur = lo
    while cur <= hi + step * 0.001:
        ticks.append(round(cur, 6))
        cur += step
    return ticks, lo, hi


def _fmt_val(v, unit="", decimals=None):
    if decimals is not None:
        s = f"{v:,.{decimals}f}"
    elif abs(v - round(v)) < 1e-6:
        s = f"{int(round(v)):,}"
    else:
        s = f"{v:,.1f}"
    return f"{s}{unit}"


VALID_CHART_TYPES = ("bar", "grouped_bar", "horizontal_bar", "line", "waterfall", "sankey")


def _esc(val):
    return html.escape(str(val), quote=True)


def _validate_chart_spec(spec):
    if not isinstance(spec, dict) or not spec:
        raise ValueError("chart spec must be a non-empty JSON object")
    if "chart_type" not in spec and not any(k in spec for k in ("data", "series", "steps", "links")):
        raise ValueError("chart spec is missing 'chart_type' and data keys ('data', 'series', 'steps', or 'links')")
    ctype = str(spec.get("chart_type") or "bar").lower()
    if ctype not in VALID_CHART_TYPES:
        raise ValueError(f"unsupported chart_type {ctype!r}; expected one of {', '.join(VALID_CHART_TYPES)}")
    if ctype in ("bar", "grouped_bar"):
        if "series" in spec:
            series_list = spec.get("series")
            if not isinstance(series_list, list) or not series_list:
                raise ValueError(f"{ctype!r} chart requires a non-empty 'series' list")
            cats = spec.get("categories") or [d.get("label") for d in (spec.get("data") or []) if isinstance(d, dict)]
            if not cats:
                raise ValueError(f"{ctype!r} chart with 'series' requires non-empty 'categories'")
            for idx, s in enumerate(series_list):
                if not isinstance(s, dict) or not isinstance(s.get("values"), list) or len(s["values"]) < len(cats):
                    raise ValueError(f"series[{idx}] must have a 'values' list with at least {len(cats)} numeric entries")
                for v in s["values"][:len(cats)]:
                    float(v)
        else:
            data = spec.get("data")
            if not isinstance(data, list) or not data:
                raise ValueError(f"{ctype!r} chart requires non-empty 'data' or 'series'")
            for idx, d in enumerate(data):
                if not isinstance(d, dict) or "label" not in d or "value" not in d:
                    raise ValueError(f"data[{idx}] must contain 'label' and 'value'")
                float(d["value"])
    elif ctype == "horizontal_bar":
        data = spec.get("data")
        if not isinstance(data, list) or not data:
            raise ValueError("'horizontal_bar' chart requires a non-empty 'data' list")
        for idx, d in enumerate(data):
            if not isinstance(d, dict) or "label" not in d or "value" not in d:
                raise ValueError(f"data[{idx}] must contain 'label' and 'value'")
            float(d["value"])
    elif ctype == "line":
        cats = spec.get("categories")
        series_list = spec.get("series")
        if not isinstance(cats, list) or not cats:
            raise ValueError("'line' chart requires a non-empty 'categories' list")
        if not isinstance(series_list, list) or not series_list:
            raise ValueError("'line' chart requires a non-empty 'series' list")
        for idx, s in enumerate(series_list):
            if not isinstance(s, dict) or not isinstance(s.get("values"), list) or len(s["values"]) < len(cats):
                raise ValueError(f"series[{idx}] must have 'values' matching 'categories' length ({len(cats)})")
            for v in s["values"][:len(cats)]:
                float(v)
    elif ctype == "waterfall":
        steps = spec.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError("'waterfall' chart requires a non-empty 'steps' list")
        for idx, st in enumerate(steps):
            if not isinstance(st, dict) or "label" not in st:
                raise ValueError(f"steps[{idx}] must contain 'label'")
            if "value" in st:
                float(st["value"])
    elif ctype == "sankey":
        links = spec.get("links")
        if not isinstance(links, list) or not links:
            raise ValueError("'sankey' chart requires a non-empty 'links' list")
        for idx, lk in enumerate(links):
            if not isinstance(lk, dict) or not all(k in lk for k in ("source", "target", "value")):
                raise ValueError(f"links[{idx}] must contain 'source', 'target', and 'value'")
            float(lk["value"])
    return ctype


def build_chart_svg(spec, theme):
    ctype = _validate_chart_spec(spec)
    vw = int(spec.get("width", 920))
    vh = int(spec.get("height", 460))
    unit = str(spec.get("unit") or "")
    decimals = spec.get("decimals")
    series_pal = theme["chart_series"]

    pad_l, pad_r, pad_t, pad_b = 76, 36, 42, 68
    has_neg_hbar = False
    if ctype == "horizontal_bar":
        has_neg_hbar = any(float(d["value"]) < 0.0 for d in (spec.get("data") or []))
        pad_l = 232 if has_neg_hbar else 180
        pad_r = 68
    plot_w = vw - pad_l - pad_r
    plot_h = vh - pad_t - pad_b

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" width="{vw}" height="{vh}" '
        f'data-chart-type="{_esc(ctype)}" role="img" aria-label="{_esc(spec.get("title") or "Chart")}">',
        f'<rect x="0" y="0" width="{vw}" height="{vh}" rx="12" fill="{_esc(theme["surface"])}"/>',
    ]

    if ctype in ("bar", "grouped_bar"):
        categories = [str(c) for c in (spec.get("categories") or [d["label"] for d in spec.get("data", [])])]
        if "series" in spec:
            series_list = spec["series"]
        else:
            series_list = [{"name": spec.get("series_name") or "Giá trị",
                            "values": [float(d["value"]) for d in spec.get("data", [])],
                            "focal_indices": [i for i, d in enumerate(spec.get("data", [])) if d.get("focal")]}]

        all_vals = [float(v) for s in series_list for v in s["values"]] + [0.0]
        ticks, y_lo, y_hi = _nice_ticks(min(0.0, min(all_vals)), max(all_vals), count=5)

        def y_pos(val):
            return pad_t + plot_h - ((val - y_lo) / (y_hi - y_lo)) * plot_h

        for tk in ticks:
            yy = y_pos(tk)
            is_zero = abs(tk) < 1e-9
            sc = theme["ink_heading"] if is_zero else theme["grid_line"]
            sw = 1.4 if is_zero else 1.0
            svg.append(f'<line x1="{pad_l}" y1="{yy:.2f}" x2="{vw-pad_r}" y2="{yy:.2f}" stroke="{_esc(sc)}" stroke-width="{sw}"/>')
            svg.append(
                f'<text x="{pad_l-10}" y="{yy+4:.2f}" text-anchor="end" font-family="JetBrains Mono, monospace" '
                f'font-size="11" fill="{_esc(theme["ink_muted"])}">{_esc(_fmt_val(tk, unit, decimals))}</text>'
            )

        n_cat = max(1, len(categories))
        n_ser = max(1, len(series_list))
        band_w = plot_w / n_cat
        group_w = band_w * 0.66
        bar_w = group_w / n_ser
        y0 = y_pos(0.0)

        # Legend if multi-series
        if n_ser > 1:
            lx = pad_l
            for s_idx, s in enumerate(series_list):
                col = s.get("color") or series_pal[s_idx % len(series_pal)]["hex"]
                sname = str(s.get("name") or f"Series {s_idx + 1}")
                svg.append(f'<rect x="{lx}" y="12" width="12" height="12" rx="3" fill="{_esc(col)}"/>')
                svg.append(f'<text x="{lx+18}" y="22" font-size="12" font-weight="600" fill="{_esc(theme["ink"])}">{_esc(sname)}</text>')
                lx += len(sname) * 7.5 + 42

        for c_idx, cat in enumerate(categories):
            gx = pad_l + c_idx * band_w + (band_w - group_w) / 2.0
            for s_idx, s in enumerate(series_list):
                val = float(s["values"][c_idx])
                sname = str(s.get("name") or f"Series {s_idx + 1}")
                bx = gx + s_idx * bar_w + 2
                bw = max(8.0, bar_w - 4)
                yv = y_pos(val)
                by = min(y0, yv)
                bh = abs(y0 - yv) if abs(val) > 1e-9 else 1.0
                focal_set = set(s.get("focal_indices") or [])
                if n_ser == 1:
                    col = series_pal[0]["hex"] if (c_idx in focal_set or not focal_set and c_idx == len(categories) - 1) else series_pal[1]["hex"]
                    if s.get("color"):
                        col = s["color"]
                else:
                    col = s.get("color") or series_pal[s_idx % len(series_pal)]["hex"]

                svg.append(
                    f'<rect class="chart-bar" x="{bx:.2f}" y="{by:.2f}" width="{bw:.2f}" height="{bh:.2f}" rx="4" '
                    f'fill="{_esc(col)}" data-label="{_esc(cat)}" data-series="{_esc(sname)}" '
                    f'data-value="{val:g}" data-zero-y="{y0:.2f}"/>'
                )
                lbl_y = by - 7 if val >= 0 else by + bh + 14
                svg.append(
                    f'<text x="{bx + bw/2:.2f}" y="{lbl_y:.2f}" text-anchor="middle" '
                    f'font-family="JetBrains Mono, monospace" font-size="11" font-weight="600" fill="{_esc(theme["ink"])}">'
                    f'{_esc(_fmt_val(val, unit, decimals))}</text>'
                )

            svg.append(
                f'<text x="{pad_l + (c_idx + 0.5)*band_w:.2f}" y="{pad_t + plot_h + 24:.2f}" '
                f'text-anchor="middle" font-size="12" font-weight="600" fill="{_esc(theme["ink"])}">{_esc(cat)}</text>'
            )

    elif ctype == "horizontal_bar":
        items = spec.get("data") or []
        vals = [float(d["value"]) for d in items] + [0.0]
        min_val = min(0.0, min(vals))
        max_val = max(0.0, max(vals))
        ticks, x_lo, x_hi = _nice_ticks(min_val, max_val, count=5)
        n_items = max(1, len(items))
        row_h = plot_h / n_items

        def x_pos(val):
            return pad_l + ((val - x_lo) / (x_hi - x_lo)) * plot_w

        for tk in ticks:
            xx = x_pos(tk)
            is_zero = abs(tk) < 1e-9
            sc = theme["ink_heading"] if is_zero else theme["grid_line"]
            sw = 1.4 if is_zero else 1.0
            svg.append(f'<line x1="{xx:.2f}" y1="{pad_t}" x2="{xx:.2f}" y2="{pad_t+plot_h}" stroke="{_esc(sc)}" stroke-width="{sw}"/>')
            svg.append(
                f'<text x="{xx:.2f}" y="{pad_t+plot_h+22}" text-anchor="middle" font-family="JetBrains Mono, monospace" '
                f'font-size="11" fill="{_esc(theme["ink_muted"])}">{_esc(_fmt_val(tk, unit, decimals))}</text>'
            )

        x0 = x_pos(0.0)
        cat_x = pad_l - 64 if has_neg_hbar else pad_l - 12
        for idx, d in enumerate(items):
            val = float(d["value"])
            lbl = str(d["label"])
            bh = min(30.0, row_h * 0.62)
            by = pad_t + idx * row_h + (row_h - bh) / 2.0
            xv = x_pos(val)
            bx = min(x0, xv)
            bw = abs(xv - x0) if abs(val) > 1e-9 else 1.0
            col = d.get("color") or (series_pal[0]["hex"] if (d.get("focal") or val < 0) else series_pal[1]["hex"])
            svg.append(
                f'<rect class="chart-hbar" x="{bx:.2f}" y="{by:.2f}" width="{bw:.2f}" height="{bh:.2f}" rx="4" '
                f'fill="{_esc(col)}" data-label="{_esc(lbl)}" data-value="{val:g}" data-zero-x="{x0:.2f}"/>'
            )
            svg.append(
                f'<text x="{cat_x:.2f}" y="{by + bh/2 + 4:.2f}" text-anchor="end" font-size="12" font-weight="600" '
                f'fill="{_esc(theme["ink"])}">{_esc(lbl)}</text>'
            )
            val_x = (bx + bw + 8) if val >= 0 else (bx - 8)
            val_anc = "start" if val >= 0 else "end"
            svg.append(
                f'<text x="{val_x:.2f}" y="{by + bh/2 + 4:.2f}" text-anchor="{val_anc}" '
                f'font-family="JetBrains Mono, monospace" font-size="11" font-weight="600" fill="{_esc(theme["ink"])}">'
                f'{_esc(_fmt_val(val, unit, decimals))}</text>'
            )

    elif ctype == "line":
        categories = [str(c) for c in spec.get("categories", [])]
        series_list = spec.get("series") or []
        all_vals = [float(v) for s in series_list for v in s["values"]]
        ticks, y_lo, y_hi = _nice_ticks(min(0.0, min(all_vals, default=0)), max(all_vals, default=1), count=5)

        def y_pos(val):
            return pad_t + plot_h - ((val - y_lo) / (y_hi - y_lo)) * plot_h

        for tk in ticks:
            yy = y_pos(tk)
            svg.append(f'<line x1="{pad_l}" y1="{yy:.2f}" x2="{vw-pad_r}" y2="{yy:.2f}" stroke="{_esc(theme["grid_line"])}" stroke-width="1"/>')
            svg.append(
                f'<text x="{pad_l-10}" y="{yy+4:.2f}" text-anchor="end" font-family="JetBrains Mono, monospace" '
                f'font-size="11" fill="{_esc(theme["ink_muted"])}">{_esc(_fmt_val(tk, unit, decimals))}</text>'
            )

        n_cat = max(2, len(categories))
        step_x = plot_w / (n_cat - 1)
        for c_idx, cat in enumerate(categories):
            xx = pad_l + c_idx * step_x
            svg.append(
                f'<text x="{xx:.2f}" y="{pad_t+plot_h+24}" text-anchor="middle" font-size="12" '
                f'fill="{_esc(theme["ink"])}">{_esc(cat)}</text>'
            )

        lx = pad_l
        for s_idx, s in enumerate(series_list):
            col = s.get("color") or series_pal[s_idx % len(series_pal)]["hex"]
            sname = str(s.get("name") or f"Series {s_idx + 1}")
            svg.append(f'<line x1="{lx}" y1="18" x2="{lx+18}" y2="18" stroke="{_esc(col)}" stroke-width="2.6"/>')
            svg.append(f'<circle cx="{lx+9}" cy="18" r="3.5" fill="{_esc(col)}"/>')
            svg.append(f'<text x="{lx+24}" y="22" font-size="12" font-weight="600" fill="{_esc(theme["ink"])}">{_esc(sname)}</text>')
            lx += len(sname) * 7.5 + 48

            pts = [(pad_l + i * step_x, y_pos(float(v)), float(v)) for i, v in enumerate(s["values"][:len(categories)])]
            d_str = " ".join(f"{'M' if i == 0 else 'L'} {px:.2f},{py:.2f}" for i, (px, py, _) in enumerate(pts))
            svg.append(f'<path d="{d_str}" fill="none" stroke="{_esc(col)}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>')
            for i, (px, py, val) in enumerate(pts):
                svg.append(
                    f'<circle class="chart-point" cx="{px:.2f}" cy="{py:.2f}" r="4.5" fill="{_esc(theme["surface"])}" '
                    f'stroke="{_esc(col)}" stroke-width="2.4" data-series="{_esc(sname)}" '
                    f'data-label="{_esc(categories[i])}" data-value="{val:g}" data-y-min="{y_lo:g}" data-y-max="{y_hi:g}"/>'
                )
                if s_idx == 0 or i in (0, len(pts) - 1):
                    svg.append(
                        f'<text x="{px:.2f}" y="{py-10:.2f}" text-anchor="middle" font-family="JetBrains Mono, monospace" '
                        f'font-size="10.5" font-weight="600" fill="{_esc(col)}">{_esc(_fmt_val(val, unit, decimals))}</text>'
                    )

    elif ctype == "waterfall":
        steps = spec.get("steps") or []
        running = 0.0
        computed = []
        bounds = [0.0]
        for st in steps:
            skind = (st.get("kind") or "delta").lower()
            val = float(st.get("value", 0.0))
            if skind == "total":
                start_v, end_v = 0.0, (val if "value" in st and st.get("explicit_total") else running)
                running = end_v
            elif skind == "start":
                start_v, end_v = 0.0, val
                running = val
            else:
                start_v, end_v = running, running + val
                running = end_v
            computed.append((str(st["label"]), skind, val if skind == "delta" else end_v, start_v, end_v))
            bounds.extend([start_v, end_v])

        ticks, y_lo, y_hi = _nice_ticks(min(0.0, min(bounds)), max(bounds), count=5)

        def y_pos(val):
            return pad_t + plot_h - ((val - y_lo) / (y_hi - y_lo)) * plot_h

        for tk in ticks:
            yy = y_pos(tk)
            sc = theme["ink_heading"] if abs(tk) < 1e-9 else theme["grid_line"]
            svg.append(f'<line x1="{pad_l}" y1="{yy:.2f}" x2="{vw-pad_r}" y2="{yy:.2f}" stroke="{_esc(sc)}" stroke-width="1"/>')
            svg.append(
                f'<text x="{pad_l-10}" y="{yy+4:.2f}" text-anchor="end" font-family="JetBrains Mono, monospace" '
                f'font-size="11" fill="{_esc(theme["ink_muted"])}">{_esc(_fmt_val(tk, unit, decimals))}</text>'
            )

        n_st = max(1, len(computed))
        band_w = plot_w / n_st
        bw = min(64.0, band_w * 0.58)
        for idx, (lbl, skind, disp_v, v0, v1) in enumerate(computed):
            bx = pad_l + idx * band_w + (band_w - bw) / 2.0
            ya, yb = y_pos(v0), y_pos(v1)
            by = min(ya, yb)
            bh = abs(ya - yb) if abs(v1 - v0) > 1e-9 else 2.0
            if skind in ("start", "total"):
                col = theme["slots"]["primary"]["stroke"]
                sign_prefix = ""
            elif v1 >= v0:
                col = theme["slots"]["secondary"]["stroke"]
                sign_prefix = "+"
            else:
                col = theme["slots"]["accent"]["stroke"]
                sign_prefix = ""

            svg.append(
                f'<rect class="waterfall-step" x="{bx:.2f}" y="{by:.2f}" width="{bw:.2f}" height="{bh:.2f}" rx="4" '
                f'fill="{_esc(col)}" data-label="{_esc(lbl)}" data-kind="{_esc(skind)}" '
                f'data-start="{v0:g}" data-end="{v1:g}" data-value="{disp_v:g}"/>'
            )
            if idx < len(computed) - 1:
                nx = pad_l + (idx + 1) * band_w + (band_w - bw) / 2.0
                yc = y_pos(v1)
                svg.append(
                    f'<line x1="{bx+bw:.2f}" y1="{yc:.2f}" x2="{nx:.2f}" y2="{yc:.2f}" '
                    f'stroke="{_esc(theme["ink_muted"])}" stroke-width="1.2" stroke-dasharray="4,3"/>'
                )
            ly = by - 7 if v1 >= v0 else by + bh + 14
            svg.append(
                f'<text x="{bx+bw/2:.2f}" y="{ly:.2f}" text-anchor="middle" font-family="JetBrains Mono, monospace" '
                f'font-size="11" font-weight="600" fill="{_esc(theme["ink"])}">'
                f'{_esc(sign_prefix + _fmt_val(disp_v, unit, decimals))}</text>'
            )
            svg.append(
                f'<text x="{bx+bw/2:.2f}" y="{pad_t+plot_h+24}" text-anchor="middle" font-size="11.5" font-weight="600" '
                f'fill="{_esc(theme["ink"])}">{_esc(lbl)}</text>'
            )

    elif ctype == "sankey":
        links = spec.get("links") or []
        out_sum = defaultdict(float)
        in_sum = defaultdict(float)
        nodes_order = []
        for lk in links:
            s, t, v = str(lk["source"]), str(lk["target"]), float(lk["value"])
            out_sum[s] += v
            in_sum[t] += v
            for nd in (s, t):
                if nd not in nodes_order:
                    nodes_order.append(nd)

        node_val = {nd: max(out_sum[nd], in_sum[nd]) for nd in nodes_order}
        # Layer nodes by simple longest-path
        ranks = {nd: 0 for nd in nodes_order}
        for _ in range(len(nodes_order)):
            for lk in links:
                s, t = str(lk["source"]), str(lk["target"])
                ranks[t] = max(ranks[t], ranks[s] + 1)
        max_r = max(ranks.values(), default=1)
        layers = defaultdict(list)
        for nd in nodes_order:
            layers[ranks[nd]].append(nd)

        max_layer_total = max((sum(node_val[n] for n in ns) for ns in layers.values()), default=1.0)
        if max_layer_total <= 0:
            max_layer_total = 1.0
        scale_k = (plot_h - 48) / max_layer_total
        node_box = {}
        col_step = (plot_w - 24) / max(1, max_r)
        for r, ns in layers.items():
            tot_h = sum(node_val[n] * scale_k for n in ns) + 20 * (len(ns) - 1)
            cy = pad_t + (plot_h - tot_h) / 2.0
            nx = pad_l + r * col_step
            for idx_n, nd in enumerate(ns):
                nh = max(14.0, node_val[nd] * scale_k)
                node_box[nd] = (nx, cy, 20.0, nh, series_pal[idx_n % len(series_pal)]["hex"])
                cy += nh + 20.0

        src_offset = defaultdict(float)
        tgt_offset = defaultdict(float)
        for idx_l, lk in enumerate(links):
            s, t, v = str(lk["source"]), str(lk["target"]), float(lk["value"])
            sx, sy, sw_n, _, scol = node_box[s]
            tx, ty, _, _, _ = node_box[t]
            fh = max(3.0, v * scale_k)
            y1 = sy + src_offset[s] + fh / 2.0
            y2 = ty + tgt_offset[t] + fh / 2.0
            src_offset[s] += fh
            tgt_offset[t] += fh
            mx = (sx + sw_n + tx) / 2.0
            d_str = f"M {sx+sw_n:.2f},{y1:.2f} C {mx:.2f},{y1:.2f} {mx:.2f},{y2:.2f} {tx:.2f},{y2:.2f}"
            svg.append(
                f'<path class="sankey-link" d="{d_str}" fill="none" stroke="{_esc(scol)}" stroke-width="{fh:.2f}" '
                f'stroke-opacity="0.34" data-source="{_esc(s)}" data-target="{_esc(t)}" data-value="{v:g}"/>'
            )

        for nd, (nx, ny, nw, nh, col) in node_box.items():
            svg.append(
                f'<rect class="sankey-node" x="{nx:.2f}" y="{ny:.2f}" width="{nw:.2f}" height="{nh:.2f}" rx="3" '
                f'fill="{_esc(col)}" data-node="{_esc(nd)}" data-value="{node_val[nd]:g}"/>'
            )
            is_right = ranks[nd] == max_r and max_r > 0
            tx_lbl = nx - 8 if is_right else nx + nw + 8
            anc = "end" if is_right else "start"
            svg.append(
                f'<text x="{tx_lbl:.2f}" y="{ny + nh/2 + 4:.2f}" text-anchor="{anc}" font-size="12" font-weight="600" '
                f'fill="{_esc(theme["ink"])}">{_esc(nd)} ({_esc(_fmt_val(node_val[nd], unit, decimals))})</text>'
            )

    svg.append("</svg>")
    return "\n".join(svg), vw, vh


def build_chart_html(spec, theme_name="tech-warm-light"):
    theme = _load_theme(theme_name)
    svg_markup, vw, _ = build_chart_svg(spec, theme)
    title = spec.get("title") or "Biểu đồ Phân tích Số liệu"
    subtitle = spec.get("subtitle") or ""
    source_note = spec.get("source") or ""
    kpis = spec.get("kpis") or []

    kpi_html = ""
    if kpis:
        cards = []
        neg_col = theme["slots"]["accent"]["stroke"]
        pos_col = theme["slots"]["success"]["stroke"]
        for k in kpis:
            d_txt = str(k.get("delta") or "")
            d_col = neg_col if d_txt.startswith("-") else (pos_col if d_txt.startswith("+") else theme["ink_muted"])
            cards.append(
                f'<div class="kpi-card">'
                f'<div class="kpi-label">{_esc(k.get("label", ""))}</div>'
                f'<div class="kpi-val">{_esc(k.get("value", ""))}</div>'
                + (f'<div class="kpi-delta" style="color:{_esc(d_col)}">{_esc(d_txt)}</div>' if d_txt else "")
                + '</div>'
            )
        kpi_html = f'<div class="kpi-strip">{"".join(cards)}</div>'

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{_esc(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&family=JetBrains+Mono:wght@500;600&display=swap" />
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 28px 24px;
      background: {theme["canvas"]};
      color: {theme["ink"]};
      font-family: 'Open Sans', 'Segoe UI', Roboto, Arial, sans-serif;
      line-height: 1.5;
    }}
    .frame {{
      max-width: {vw + 48}px;
      margin: 0 auto;
    }}
    .eyebrow {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: {theme["edge_critical"]};
      margin-bottom: 6px;
    }}
    .eyebrow::before {{
      content: "";
      width: 28px;
      height: 2px;
      background: currentColor;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 24px;
      line-height: 1.25;
      color: {theme["ink_heading"]};
    }}
    .subtitle {{
      margin: 0 0 18px;
      font-size: 14px;
      color: {theme["ink_muted"]};
    }}
    .kpi-strip {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }}
    .kpi-card {{
      background: {theme["surface"]};
      border: 1px solid {theme["border_subtle"]};
      border-radius: 10px;
      padding: 12px 16px;
    }}
    .kpi-label {{
      font-size: 12px;
      color: {theme["ink_muted"]};
    }}
    .kpi-val {{
      font-family: 'JetBrains Mono', monospace;
      font-size: 22px;
      font-weight: 600;
      color: {theme["ink_heading"]};
      margin-top: 2px;
    }}
    .kpi-delta {{
      font-size: 12px;
      font-weight: 600;
      margin-top: 2px;
    }}
    .chart-box {{
      border: 1px solid {theme["border_subtle"]};
      border-radius: 12px;
      background: {theme["surface"]};
      overflow: hidden;
    }}
    .chart-box svg {{
      display: block;
      width: 100%;
      height: auto;
    }}
    .source {{
      margin-top: 10px;
      font-size: 12px;
      color: {theme["ink_muted"]};
    }}
  </style>
</head>
<body>
  <main class="frame">
    {f'<div class="eyebrow">{_esc(spec["eyebrow"])}</div>' if spec.get("eyebrow") else ''}
    <h1>{_esc(title)}</h1>
    {f'<p class="subtitle">{_esc(subtitle)}</p>' if subtitle else ''}
    {kpi_html}
    <div class="chart-box">
      {svg_markup}
    </div>
    {f'<div class="source">{_esc(source_note)}</div>' if source_note else ''}
  </main>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description="Build an HTML+SVG quantitative chart with data-* honesty attributes.")
    ap.add_argument("spec", help="JSON chart spec file")
    ap.add_argument("-o", "--output", required=True, help="Output .html path")
    ap.add_argument("--theme", default="tech-warm-light", choices=["tech-warm-light", "tech-warm-dark"])
    ap.add_argument("--svg", default=None, help="Optional standalone .svg output path")
    args = ap.parse_args()

    try:
        with open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)

        html_doc = build_chart_html(spec, theme_name=args.theme)
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html_doc)
        sys.stderr.write(f"wrote {args.output}\n")

        if args.svg:
            theme = _load_theme(args.theme)
            svg_markup, _, _ = build_chart_svg(spec, theme)
            svg_standalone = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                + svg_markup.replace(
                    "<rect ",
                    '<defs><style>@import url("https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&amp;family=JetBrains+Mono:wght@500;600&amp;display=swap");'
                    ' text { font-family: "Open Sans", "Segoe UI", Arial, sans-serif; }</style></defs><rect ',
                    1
                )
                + "\n"
            )
            os.makedirs(os.path.dirname(os.path.abspath(args.svg)), exist_ok=True)
            with open(args.svg, "w", encoding="utf-8") as f:
                f.write(svg_standalone)
            sys.stderr.write(f"wrote {args.svg}\n")
    except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
