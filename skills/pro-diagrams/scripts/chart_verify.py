#!/usr/bin/env python3
"""Verify quantitative HTML+SVG charts for `data-*` proportional honesty, viewBox bounds, and WCAG AA.

Checks:
  1. UTF-8 integrity (no replacement character U+FFFD) & valid 4-number SVG viewBox
  2. Bar / Horizontal Bar proportionality (`height` or `width` strictly proportional to `|data-value|`, including diverging negative bars)
  3. Waterfall step arithmetic (`start + delta == end`, total matches running cumulative sum) & height proportionality (`<= 3%`)
  4. Line point vertical placement (`cy` strictly linear with `data-value`, `<= 3%` tolerance, handling constant series)
  5. Sankey positive flow & internal-node flow conservation (`sum(in) == sum(out)`)
  6. WCAG 2.1 AA text contrast on explicit SVG `<text>` and HTML/CSS pairs (`>= 4.5:1` normal, `>= 3.0:1` large)

Usage:
  python3 chart_verify.py chart.html [--json]
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})

_NAMED_COLORS = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "silver": (192, 192, 192),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "navy": (0, 0, 128),
    "teal": (0, 128, 128),
    "maroon": (128, 0, 0),
}


def _parse_color(color_str):
    if not color_str:
        return None
    c = str(color_str).strip()
    if not c or c.lower() in ("none", "transparent", "inherit", "initial", "currentcolor"):
        return None
    # Handle shorthand background declarations like "#F8F6F2 none repeat"
    token = c.split()[0] if " " in c and not c.lower().startswith("rgb") else c
    m3 = re.fullmatch(r"#([0-9a-fA-F]{3})", token)
    if m3:
        h = m3.group(1)
        token = f"#{h[0]*2}{h[1]*2}{h[2]*2}"
    m6 = re.fullmatch(r"#([0-9a-fA-F]{6})", token)
    if m6:
        h = m6.group(1)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    mrgb = re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", c, re.IGNORECASE)
    if mrgb:
        r, g, b = int(mrgb.group(1)), int(mrgb.group(2)), int(mrgb.group(3))
        if all(0 <= ch <= 255 for ch in (r, g, b)):
            return r, g, b
    return _NAMED_COLORS.get(token.lower())


def _relative_luminance(rgb):
    def _lin(ch):
        s = ch / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast_ratio(fg_color, bg_color):
    c1 = _parse_color(fg_color)
    c2 = _parse_color(bg_color)
    if c1 is None or c2 is None:
        return None
    l1 = _relative_luminance(c1)
    l2 = _relative_luminance(c2)
    hi, lo = (l1, l2) if l1 >= l2 else (l2, l1)
    return (hi + 0.05) / (lo + 0.05)


def _parse_inline_style(style_str):
    out = {}
    if not style_str:
        return out
    for decl in style_str.split(";"):
        if ":" in decl:
            k, v = decl.split(":", 1)
            k = k.strip().lower()
            v = v.strip()
            if k and v:
                out[k] = v
    return out


def _parse_css_rules(css_text):
    """Extract simple tag and .class selector declarations from <style> text."""
    rules = defaultdict(dict)
    cleaned = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
    # Remove @import / @charset rules
    cleaned = re.sub(r"@[^{;]+;", "", cleaned)
    for m in re.finditer(r"([^{}@]+)\{([^{}]*)\}", cleaned):
        sels_raw, body = m.group(1), m.group(2)
        decls = _parse_inline_style(body)
        if not decls:
            continue
        for sel in sels_raw.split(","):
            sel = sel.strip()
            # Match simple selectors like body, h1, .kpi-card, div.kpi-delta
            if not sel or ":" in sel or " " in sel or ">" in sel or "+" in sel or "~" in sel:
                continue
            rules[sel.lower()].update(decls)
    return rules


def _parse_font_size(val, default=12.0):
    if val is None:
        return default
    s = str(val).strip().lower()
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(px|pt)?$", s)
    if not m:
        return default
    num = float(m.group(1))
    unit = m.group(2)
    if unit == "pt":
        return num * (4.0 / 3.0)
    return num


def _is_bold_weight(val):
    if val is None:
        return False
    s = str(val).strip().lower()
    if "bold" in s:
        return True
    try:
        return float(s) >= 700.0
    except ValueError:
        return False


def _safe_float(d, key):
    if key not in d:
        return None
    try:
        v = float(d[key])
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None


class _ChartHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.svgs = []
        self.bars = []
        self.hbars = []
        self.points = []
        self.waterfall = []
        self.sankey_links = []
        self.sankey_nodes = []
        self.css_blocks = []
        self.svg_texts = []
        self.html_texts = []

        self._stack = []
        self._in_style = False
        self._style_buf = []
        self._svg_depth = 0
        self._cur_svg_idx = -1
        self._svg_rects = defaultdict(list)
        self._svg_bg = {}
        self._cur_svg_text = None

    def _record_element(self, tag, attrs, self_closing=False):
        t = tag.lower()
        d = {k.lower(): (v or "") for k, v in attrs}
        cls = set(d.get("class", "").split())
        inline = _parse_inline_style(d.get("style", ""))

        if t == "style":
            if not self_closing:
                self._in_style = True
                self._style_buf = []
            return

        if t == "svg":
            self._cur_svg_idx = len(self.svgs)
            self._svg_depth += 1
            ancestors = list(self._stack)
            self.svgs.append({"attrs": d, "ancestors": ancestors})
            if not self_closing:
                self._stack.append((t, cls, inline))
            else:
                self._svg_depth -= 1
                self._cur_svg_idx = -1
            return

        if self._svg_depth > 0:
            svg_idx = self._cur_svg_idx
            item = dict(d)
            item["_svg_idx"] = svg_idx
            if "chart-bar" in cls or (t == "rect" and "data-value" in d and "data-zero-y" in d):
                self.bars.append(item)
            elif "chart-hbar" in cls or (t == "rect" and "data-value" in d and "data-zero-x" in d):
                self.hbars.append(item)
            elif "chart-point" in cls or (t == "circle" and "data-value" in d and "data-y-min" in d):
                self.points.append(item)
            elif "waterfall-step" in cls or (t == "rect" and "data-kind" in d and "data-start" in d):
                self.waterfall.append(item)
            elif "sankey-link" in cls or (t == "path" and "data-source" in d and "data-target" in d):
                self.sankey_links.append(item)
            elif "sankey-node" in cls or (t == "rect" and "data-node" in d):
                self.sankey_nodes.append(item)

            if t == "rect":
                fill_val = inline.get("fill") or d.get("fill", "")
                f_op = _safe_float(d, "fill-opacity")
                if f_op is None and "fill-opacity" in inline:
                    try:
                        f_op = float(inline["fill-opacity"])
                    except ValueError:
                        f_op = None
                if _parse_color(fill_val) is not None and (f_op is None or f_op >= 0.5):
                    rx = _safe_float(d, "x")
                    ry = _safe_float(d, "y")
                    rw = _safe_float(d, "width")
                    rh = _safe_float(d, "height")
                    is_pct_full = d.get("width", "").strip() == "100%" and d.get("height", "").strip() == "100%"
                    if is_pct_full:
                        self._svg_bg[svg_idx] = fill_val
                    elif rw is not None and rh is not None and rw > 0 and rh > 0:
                        rx = 0.0 if rx is None else rx
                        ry = 0.0 if ry is None else ry
                        self._svg_rects[svg_idx].append((rx, ry, rw, rh, fill_val))
                        if svg_idx not in self._svg_bg and abs(rx) <= 1.0 and abs(ry) <= 1.0:
                            vb = self.svgs[svg_idx]["attrs"].get("viewbox", "").split()
                            if len(vb) == 4:
                                try:
                                    vb_w, vb_h = float(vb[2]), float(vb[3])
                                    if rw >= vb_w * 0.9 and rh >= vb_h * 0.9:
                                        self._svg_bg[svg_idx] = fill_val
                                except ValueError:
                                    pass
            elif t == "text" and not self_closing:
                self._cur_svg_text = {
                    "svg_idx": svg_idx,
                    "attrs": d,
                    "inline": inline,
                    "rects_snapshot": list(self._svg_rects[svg_idx]),
                    "text_parts": [],
                }
            if not self_closing and t not in _VOID_TAGS:
                self._stack.append((t, cls, inline))
            return

        if not self_closing and t not in _VOID_TAGS:
            self._stack.append((t, cls, inline))

    def handle_starttag(self, tag, attrs):
        self._record_element(tag, attrs, self_closing=False)

    def handle_startendtag(self, tag, attrs):
        self._record_element(tag, attrs, self_closing=True)

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == "style" and self._in_style:
            self._in_style = False
            self.css_blocks.append("".join(self._style_buf))
            self._style_buf = []
            return
        if t == "text" and self._cur_svg_text is not None:
            txt = "".join(self._cur_svg_text["text_parts"]).strip()
            if txt:
                self._cur_svg_text["text"] = txt
                self.svg_texts.append(self._cur_svg_text)
            self._cur_svg_text = None
        if t in _VOID_TAGS:
            return
        if t == "svg" and self._svg_depth > 0:
            self._svg_depth -= 1
            if self._svg_depth == 0:
                self._cur_svg_idx = -1
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == t:
                del self._stack[i:]
                break

    def handle_data(self, data):
        if self._in_style:
            self._style_buf.append(data)
            return
        if self._cur_svg_text is not None:
            self._cur_svg_text["text_parts"].append(data)
            return
        if self._svg_depth > 0:
            return
        txt = data.strip()
        if not txt:
            return
        anc_tags = {el[0] for el in self._stack}
        if anc_tags & {"head", "title", "script", "style", "noscript"}:
            return
        if self._stack:
            self.html_texts.append((list(self._stack), txt))


def _resolve_chain_style(chain, css_rules):
    bg = None
    fg = None
    fsize = 16.0
    fweight = "400"
    for tag, cls_set, inline in chain:
        # Apply tag rule, then class rules, then tag.class rules, then inline style
        matched = []
        if tag in css_rules:
            matched.append(css_rules[tag])
        for c in sorted(cls_set):
            if f".{c}" in css_rules:
                matched.append(css_rules[f".{c}"])
            if f"{tag}.{c}" in css_rules:
                matched.append(css_rules[f"{tag}.{c}"])
        matched.append(inline)
        for decls in matched:
            cand_bg = decls.get("background-color") or decls.get("background")
            if cand_bg and _parse_color(cand_bg) is not None:
                bg = cand_bg
            cand_fg = decls.get("color")
            if cand_fg and _parse_color(cand_fg) is not None:
                fg = cand_fg
            if "font-size" in decls:
                fsize = _parse_font_size(decls["font-size"], default=fsize)
            if "font-weight" in decls:
                fweight = decls["font-weight"]
    return fg, bg, fsize, fweight


def _find_svg_text_bg(text_entry, svg_default_bg):
    d = text_entry["attrs"]
    tx = _safe_float(d, "x")
    ty = _safe_float(d, "y")
    fsize = _parse_font_size(text_entry["inline"].get("font-size") or d.get("font-size"), default=12.0)
    if tx is not None and ty is not None:
        # Mid-cap vertical position is slightly above SVG text baseline `ty`
        mid_y = ty - fsize * 0.35
        for rx, ry, rw, rh, fill_val in reversed(text_entry["rects_snapshot"]):
            if rx <= tx <= rx + rw and ry <= mid_y <= ry + rh:
                return fill_val
    return svg_default_bg


def verify_chart_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    except UnicodeDecodeError as exc:
        return {
            "file": path,
            "passed": False,
            "marks_verified": 0,
            "errors": [f"E-UTF8-DECODE: invalid UTF-8 in {path}: {exc}"],
            "warnings": [],
        }

    errors = []
    warnings = []

    if "\ufffd" in raw:
        errors.append("E-UTF8-MOJIBAKE: replacement character U+FFFD found in document")

    p = _ChartHTMLParser()
    p.feed(raw)
    p.close()

    if not p.svgs:
        errors.append("E-NO-SVG: no <svg> element found in chart file")
        return {
            "file": path,
            "passed": False,
            "marks_verified": 0,
            "errors": errors,
            "warnings": warnings,
        }

    for i, svg_info in enumerate(p.svgs):
        vb = svg_info["attrs"].get("viewbox", "").split()
        if len(vb) != 4:
            errors.append(f"E-VIEWBOX: svg #{i+1} missing valid 4-number viewBox")
        else:
            try:
                _, _, vbw, vbh = [float(x) for x in vb]
                if not (math.isfinite(vbw) and math.isfinite(vbh) and vbw > 0 and vbh > 0):
                    errors.append(f"E-VIEWBOX: svg #{i+1} has non-positive viewBox dimensions")
            except ValueError:
                errors.append(f"E-VIEWBOX: svg #{i+1} viewBox contains non-numeric values")

    total_data_marks = (
        len(p.bars) + len(p.hbars) + len(p.points) + len(p.waterfall) + len(p.sankey_links)
    )
    if total_data_marks == 0:
        errors.append("E-NO-DATA-ATTRS: no data-* annotated marks (.chart-bar, .chart-hbar, .chart-point, .waterfall-step, .sankey-link) found")

    # 1. Verify vertical bar proportionality (scoped per SVG)
    bars_by_svg = defaultdict(list)
    for b in p.bars:
        bars_by_svg[b["_svg_idx"]].append(b)
    for svg_idx, bars in bars_by_svg.items():
        nonzero_bars = []
        for b in bars:
            lbl = b.get("data-label", "?")
            v = _safe_float(b, "data-value")
            h = _safe_float(b, "height")
            if v is None or h is None:
                errors.append(f"E-BAR-HONESTY: bar {lbl!r} missing numeric data-value or height")
                continue
            if abs(v) > 1e-6:
                if h <= 0:
                    errors.append(f"E-BAR-HONESTY: bar {lbl!r} (value={v}) has non-positive height={h}")
                else:
                    nonzero_bars.append((v, h, lbl))
        if len(nonzero_bars) >= 2:
            ratios = [h / abs(v) for v, h, _ in nonzero_bars]
            mean_r = sum(ratios) / len(ratios)
            for (v, h, lbl), r in zip(nonzero_bars, ratios):
                if mean_r > 0 and abs(r - mean_r) / mean_r > 0.03:
                    errors.append(
                        f"E-BAR-HONESTY: bar {lbl!r} (value={v}, height={h}) deviates >3% from linear scale"
                    )

    # 2. Verify horizontal bar proportionality & diverging zero-baseline direction
    hbars_by_svg = defaultdict(list)
    for b in p.hbars:
        hbars_by_svg[b["_svg_idx"]].append(b)
    for svg_idx, hbars in hbars_by_svg.items():
        nonzero_hbars = []
        for b in hbars:
            lbl = b.get("data-label", "?")
            v = _safe_float(b, "data-value")
            w = _safe_float(b, "width")
            if v is None or w is None:
                errors.append(f"E-HBAR-HONESTY: horizontal bar {lbl!r} missing numeric data-value or width")
                continue
            bx = _safe_float(b, "x")
            z0 = _safe_float(b, "data-zero-x")
            if abs(v) > 1e-6:
                if w <= 0:
                    errors.append(f"E-HBAR-HONESTY: horizontal bar {lbl!r} (value={v}) has non-positive width={w}")
                    continue
                if bx is not None and z0 is not None:
                    if v < 0 and (bx > z0 + 1.0 or bx + w > z0 + 1.5):
                        errors.append(
                            f"E-HBAR-HONESTY: negative horizontal bar {lbl!r} (value={v}) does not extend left of zero baseline"
                        )
                    elif v > 0 and bx < z0 - 1.5:
                        errors.append(
                            f"E-HBAR-HONESTY: positive horizontal bar {lbl!r} (value={v}) does not extend right of zero baseline"
                        )
                nonzero_hbars.append((v, w, lbl))
        if len(nonzero_hbars) >= 2:
            ratios = [w / abs(v) for v, w, _ in nonzero_hbars]
            mean_r = sum(ratios) / len(ratios)
            for (v, w, lbl), r in zip(nonzero_hbars, ratios):
                if mean_r > 0 and abs(r - mean_r) / mean_r > 0.03:
                    errors.append(
                        f"E-HBAR-HONESTY: horizontal bar {lbl!r} (value={v}, width={w}) deviates >3% from linear scale"
                    )

    # 3. Verify line point linear cy proportionality
    pts_by_svg = defaultdict(list)
    for pt in p.points:
        pts_by_svg[pt["_svg_idx"]].append(pt)
    for svg_idx, pts in pts_by_svg.items():
        parsed_pts = []
        for pt in pts:
            lbl = pt.get("data-label", "?")
            v = _safe_float(pt, "data-value")
            cy = _safe_float(pt, "cy")
            ylo = _safe_float(pt, "data-y-min")
            yhi = _safe_float(pt, "data-y-max")
            if v is None or cy is None:
                errors.append(f"E-LINE-HONESTY: point {lbl!r} missing numeric data-value or cy")
                continue
            if ylo is not None and yhi is not None and yhi > ylo:
                frac = (v - ylo) / (yhi - ylo)
            else:
                frac = v
            parsed_pts.append((v, frac, cy, lbl))

        if len(parsed_pts) >= 2:
            fracs = [item[1] for item in parsed_pts]
            cys = [item[2] for item in parsed_pts]
            f_span = max(fracs) - min(fracs)
            if f_span < 1e-9:
                # Constant series: all cy coordinates should match
                if max(cys) - min(cys) > 1.5:
                    errors.append(
                        f"E-LINE-HONESTY: constant-value line points have inconsistent cy coordinates (spread={max(cys)-min(cys):.2f}px)"
                    )
            else:
                # Fit linear model cy = intercept + slope * frac (SVG y increases downward => slope < 0)
                n_pts = len(parsed_pts)
                mean_f = sum(fracs) / n_pts
                mean_y = sum(cys) / n_pts
                ss_ff = sum((f - mean_f) ** 2 for f in fracs)
                ss_fy = sum((f - mean_f) * (y - mean_y) for f, y in zip(fracs, cys))
                slope = ss_fy / ss_ff
                intercept = mean_y - slope * mean_f
                if slope >= -1e-6:
                    errors.append(
                        f"E-LINE-HONESTY: line chart y-axis orientation invalid (higher values do not map to smaller cy; slope={slope:.3f})"
                    )
                else:
                    cy_span = abs(slope) * f_span
                    tol_px = max(0.5, 0.03 * cy_span)
                    for v, f_val, cy_val, lbl in parsed_pts:
                        cy_pred = intercept + slope * f_val
                        if abs(cy_val - cy_pred) > tol_px:
                            errors.append(
                                f"E-LINE-HONESTY: point {lbl!r} (value={v:g}, cy={cy_val:.2f}) deviates >3% from linear y-scale (expected {cy_pred:.2f})"
                            )

    # 4. Verify Waterfall arithmetic & height proportionality
    wf_by_svg = defaultdict(list)
    for st in p.waterfall:
        wf_by_svg[st["_svg_idx"]].append(st)
    for svg_idx, wf_steps in wf_by_svg.items():
        running = None
        nonzero_wf = []
        for st in wf_steps:
            lbl = st.get("data-label", "?")
            kind = st.get("data-kind", "delta")
            v_start = _safe_float(st, "data-start")
            v_end = _safe_float(st, "data-end")
            v_val = _safe_float(st, "data-value")
            h_px = _safe_float(st, "height")
            if v_start is None or v_end is None or v_val is None:
                errors.append(f"E-WATERFALL-MATH: step {lbl!r} missing numeric data-start/data-end/data-value")
                continue
            if kind == "start":
                running = v_end
            elif kind == "delta":
                if running is not None and abs(v_start - running) > 1e-3:
                    errors.append(f"E-WATERFALL-CONTINUITY: step {lbl!r} starts at {v_start}, expected {running}")
                if abs((v_start + v_val) - v_end) > 1e-3:
                    errors.append(f"E-WATERFALL-MATH: step {lbl!r} {v_start} + {v_val} != {v_end}")
                running = v_end
            elif kind == "total":
                if running is not None and abs(v_end - running) > 1e-2:
                    errors.append(f"E-WATERFALL-TOTAL: total {lbl!r} shows {v_end}, cumulative sum is {running}")
                running = v_end

            if abs(v_val) > 1e-6:
                if h_px is None or h_px <= 0:
                    errors.append(
                        f"E-WATERFALL-PROPORTION: step {lbl!r} (value={v_val:g}) missing positive rect height"
                    )
                else:
                    nonzero_wf.append((v_val, h_px, lbl))

        if len(nonzero_wf) >= 2:
            ratios = [h / abs(v) for v, h, _ in nonzero_wf]
            mean_r = sum(ratios) / len(ratios)
            for (v, h, lbl), r in zip(nonzero_wf, ratios):
                if mean_r > 0 and abs(r - mean_r) / mean_r > 0.03:
                    errors.append(
                        f"E-WATERFALL-PROPORTION: step {lbl!r} (value={v:g}, height={h:.2f}) deviates >3% from linear scale"
                    )

    # 5. Verify Sankey positive flow & internal-node flow conservation
    links_by_svg = defaultdict(list)
    for lk in p.sankey_links:
        links_by_svg[lk["_svg_idx"]].append(lk)
    nodes_by_svg = defaultdict(list)
    for nd in p.sankey_nodes:
        nodes_by_svg[nd["_svg_idx"]].append(nd)

    for svg_idx, links in links_by_svg.items():
        in_sum = defaultdict(float)
        out_sum = defaultdict(float)
        for lk in links:
            src = lk.get("data-source", "")
            tgt = lk.get("data-target", "")
            val = _safe_float(lk, "data-value")
            if val is None or val <= 0:
                errors.append(f"E-SANKEY-NONPOS: link {src}->{tgt} has non-positive value")
            else:
                out_sum[src] += val
                in_sum[tgt] += val

        all_nodes = set(in_sum.keys()) | set(out_sum.keys())
        for nd in sorted(all_nodes):
            iv, ov = in_sum[nd], out_sum[nd]
            if iv > 0 and ov > 0:
                ref = max(iv, ov)
                if abs(iv - ov) > max(1e-6, 0.01 * ref):
                    errors.append(
                        f"E-SANKEY-CONSERVATION: internal node {nd!r} flow not conserved (in={iv:g}, out={ov:g})"
                    )

        for nd_el in nodes_by_svg.get(svg_idx, []):
            nd_name = nd_el.get("data-node", "")
            nd_val = _safe_float(nd_el, "data-value")
            if nd_name in all_nodes and nd_val is not None:
                expected = max(in_sum[nd_name], out_sum[nd_name])
                if nd_val <= 0:
                    errors.append(f"E-SANKEY-NONPOS: node {nd_name!r} has non-positive value {nd_val:g}")
                elif expected > 0 and abs(nd_val - expected) > max(1e-6, 0.01 * expected):
                    errors.append(
                        f"E-SANKEY-CONSERVATION: node {nd_name!r} data-value={nd_val:g} mismatches link flow sum {expected:g}"
                    )

    # 6. WCAG 2.1 AA Contrast Check on SVG <text> and HTML/CSS elements
    css_rules = _parse_css_rules("\n".join(p.css_blocks))
    seen_wcag = set()

    # 6a. Check SVG <text> elements against their enclosing rect / SVG canvas background
    for t_entry in p.svg_texts:
        d = t_entry["attrs"]
        inline = t_entry["inline"]
        fg = inline.get("fill") or d.get("fill")
        if not fg or _parse_color(fg) is None:
            continue
        svg_idx = t_entry["svg_idx"]
        _, parent_bg, _, _ = _resolve_chain_style(p.svgs[svg_idx]["ancestors"], css_rules)
        svg_default_bg = p._svg_bg.get(svg_idx) or parent_bg or "#FFFFFF"
        bg = _find_svg_text_bg(t_entry, svg_default_bg)
        ratio = _contrast_ratio(fg, bg)
        if ratio is None:
            continue
        fsize = _parse_font_size(inline.get("font-size") or d.get("font-size"), default=12.0)
        fweight = inline.get("font-weight") or d.get("font-weight")
        is_large = (fsize >= 18.0) or (_is_bold_weight(fweight) and fsize >= 14.0)
        req = 3.0 if is_large else 4.5
        if ratio < req:
            key = ("svg", fg.lower(), bg.lower(), round(req, 1))
            if key not in seen_wcag:
                seen_wcag.add(key)
                snippet = t_entry["text"][:32]
                errors.append(
                    f"E-WCAG-CONTRAST: SVG text {snippet!r} ({fg} on {bg}) contrast {ratio:.2f}:1 < {req:.1f}:1 WCAG AA"
                )

    # 6b. Check HTML text elements (e.g. .kpi-delta on .kpi-card, headings, labels)
    for chain, txt in p.html_texts:
        fg, bg, fsize, fweight = _resolve_chain_style(chain, css_rules)
        if fg is None or bg is None:
            continue
        ratio = _contrast_ratio(fg, bg)
        if ratio is None:
            continue
        is_large = (fsize >= 18.0) or (_is_bold_weight(fweight) and fsize >= 14.0)
        req = 3.0 if is_large else 4.5
        if ratio < req:
            key = ("html", fg.lower(), bg.lower(), round(req, 1))
            if key not in seen_wcag:
                seen_wcag.add(key)
                snippet = txt[:32]
                errors.append(
                    f"E-WCAG-CONTRAST: HTML text {snippet!r} ({fg} on {bg}) contrast {ratio:.2f}:1 < {req:.1f}:1 WCAG AA"
                )

    return {
        "file": path,
        "passed": len(errors) == 0,
        "marks_verified": total_data_marks,
        "errors": errors,
        "warnings": warnings,
    }


def main():
    ap = argparse.ArgumentParser(description="Verify HTML+SVG quantitative chart data-* honesty.")
    ap.add_argument("file", help="Path to chart .html or .svg")
    ap.add_argument("--json", action="store_true", help="Output JSON report")
    args = ap.parse_args()

    try:
        res = verify_chart_file(args.file)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        sys.exit(1)

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        for e in res["errors"]:
            print(f"error: {e}")
        for w in res["warnings"]:
            print(f"warning: {w}")
        status = "CHART VERIFY PASS" if res["passed"] else "CHART VERIFY FAIL"
        print(f"[{status}] verified {res['marks_verified']} data-* mark(s), {len(res['errors'])} error(s)")
    sys.exit(0 if res["passed"] else 1)


if __name__ == "__main__":
    main()
