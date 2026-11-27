#!/usr/bin/env python3
"""Zero-dependency pure-Python renderer from .drawio XML to standalone SVG, HTML, and PNG.

Supports all 26 ISO 5807:1985 + extended flowchart shapes (including Card §9.1.2.6,
Paper Tape §9.1.2.7, Ellipsis §9.4.4, and §10.3.2 stacked multi-document labels),
ISO 5807 §9.3 line markers (bidirectional arrows, Control Transfer triangle P/T/I,
Communication Link zigzag), horizontal & vertical Pools/Swimlanes, rounded orthogonal
edges, Open Sans Vietnamese multi-line text wrapping, and interactive HTML viewing.

Usage:
  python3 drawio_render_svg.py diagram.drawio -o diagram.svg [--html diagram.html] [--png diagram.png]
"""
import argparse
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import urllib.parse
import xml.etree.ElementTree as ET

GOOGLE_FONTS_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,400;0,600;0,700;1,400"
    "&amp;family=JetBrains+Mono:wght@400;600&amp;display=swap');"
)


def _esc_attr(val):
    return html.escape(str(val or ""), quote=True)


def _parse_style(style_str):
    d = {"_flags": set()}
    for part in (style_str or "").split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            d[k.strip()] = v.strip()
        else:
            d["_flags"].add(part)
    return d


def _parse_overlay_items(st):
    raw = st.get("isoOverlayItems")
    if not raw:
        return None
    try:
        val = json.loads(urllib.parse.unquote(raw))
        if isinstance(val, list) and val:
            return [str(v) for v in val]
    except (ValueError, TypeError):
        pass
    return None


def _strip_html_lines(raw):
    if not raw:
        return []
    s = re.sub(r"<br\s*/?>", "\n", str(raw), flags=re.I)
    lines = []
    for raw_line in s.split("\n"):
        is_bold = bool(re.search(r"<\s*b\b", raw_line, flags=re.I))
        m_sz = re.search(r"font-size\s*:\s*(\d+)px", raw_line, flags=re.I)
        m_col = re.search(r"color\s*:\s*(#[0-9A-Fa-f]{6})", raw_line, flags=re.I)
        clean = html.unescape(re.sub(r"<[^>]+>", "", raw_line)).strip()
        if clean:
            lines.append({
                "text": clean,
                "bold": is_bold,
                "font_size": int(m_sz.group(1)) if m_sz else None,
                "color": m_col.group(1) if m_col else None,
            })
    return lines


def _wrap_rich_lines(rich_lines, box_w, base_fsize, shape_kind):
    eff_w = box_w * (
        0.62 if shape_kind == "diamond"
        else (0.76 if shape_kind in ("parallelogram", "hexagon", "predefined", "card", "paper_tape") else 0.86)
    )
    out = []
    for item in rich_lines:
        fs = item["font_size"] or base_fsize
        max_chars = max(8, int(eff_w / max(5.5, fs * 0.57)))
        chunks = textwrap.wrap(item["text"], width=max_chars, break_long_words=False, break_on_hyphens=False) or [item["text"]]
        for ch in chunks:
            out.append({
                "text": ch,
                "bold": item["bold"],
                "font_size": fs,
                "color": item["color"],
            })
    return out


def _detect_shape(st):
    flags = st["_flags"]
    sh = (st.get("shape") or "").lower()
    if (st.get("isoSymbol") or "").lower() == "ellipsis":
        return "ellipsis"
    if "swimlane" in flags or sh == "swimlane":
        return "swimlane"
    if "text" in flags:
        return "text"
    if "mxgraph.flowchart.terminator" in sh or (st.get("rounded") == "1" and float(st.get("arcSize", 0) or 0) >= 40):
        return "stadium"
    if "mxgraph.flowchart.decision" in sh or "rhombus" in flags or sh == "rhombus":
        return "diamond"
    if sh == "parallelogram" or "mxgraph.flowchart.data" in sh:
        return "parallelogram"
    if sh == "process" or "predefined" in sh:
        return "predefined"
    if "multi-document" in sh:
        return "multi_document"
    if "document" in sh:
        return "document"
    if "database" in sh or "cylinder" in sh:
        return "cylinder"
    if "direct_data" in sh:
        return "direct_data"
    if "stored_data" in sh or sh == "datastorage":
        return "stored_data"
    if "sequential_data" in sh:
        return "sequential_data"
    if sh == "internalstorage":
        return "internal_storage"
    if sh == "card" or "mxgraph.flowchart.card" in sh:
        return "card"
    if sh == "tape" or "paper_tape" in sh or "punched_tape" in sh:
        return "paper_tape"
    if sh == "hexagon":
        return "hexagon"
    if sh == "trapezoid":
        return "manual_op" if st.get("flipV") == "1" else "trapezoid"
    if sh == "manualinput":
        return "manual_input"
    if "on-page_reference" in sh or "ellipse" in flags or sh == "ellipse":
        return "circle"
    if sh == "offpageconnector":
        return "off_page"
    if "loop_limit" in sh:
        return "loop_end" if st.get("flipV") == "1" else "loop_start"
    if "delay" in sh:
        return "delay"
    if "display" in sh:
        return "display"
    if "parallel_mode" in sh:
        return "parallel_mode"
    if "annotation" in sh:
        return "annotation"
    return "rounded_rect" if st.get("rounded") == "1" else "rect"


def _render_shape_svg(kind, x, y, w, h, st):
    fill = st.get("fillColor", "#FFFFFF")
    fill_attr = "none" if fill == "none" else _esc_attr(fill)
    stroke = st.get("strokeColor", "#4A5860")
    stroke_attr = "none" if stroke == "none" else _esc_attr(stroke)
    sw = float(st.get("strokeWidth", 1.5) or 1.5)
    dash = ' stroke-dasharray="5,4"' if st.get("dashed") == "1" else ""
    common = f'fill="{fill_attr}" stroke="{stroke_attr}" stroke-width="{sw:g}" stroke-linejoin="round"{dash}'
    cx, cy = x + w / 2.0, y + h / 2.0

    if kind == "text":
        return ""
    if kind == "stadium":
        r = min(w, h) / 2.0
        return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{r:g}" ry="{r:g}" {common}/>'
    if kind == "rounded_rect":
        r = min(10.0, min(w, h) * 0.16)
        return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{r:g}" ry="{r:g}" {common}/>'
    if kind == "rect":
        return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="2" ry="2" {common}/>'
    if kind == "diamond":
        pts = f"{cx:g},{y:g} {x+w:g},{cy:g} {cx:g},{y+h:g} {x:g},{cy:g}"
        return f'<polygon points="{pts}" {common}/>'
    if kind == "parallelogram":
        dx = min(24.0, w * 0.15)
        pts = f"{x+dx:g},{y:g} {x+w:g},{y:g} {x+w-dx:g},{y+h:g} {x:g},{y+h:g}"
        return f'<polygon points="{pts}" {common}/>'
    if kind == "predefined":
        ins = max(12.0, w * 0.10)
        return (
            f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="2" {common}/>'
            f'<line x1="{x+ins:g}" y1="{y:g}" x2="{x+ins:g}" y2="{y+h:g}" stroke="{stroke_attr}" stroke-width="{sw:g}"/>'
            f'<line x1="{x+w-ins:g}" y1="{y:g}" x2="{x+w-ins:g}" y2="{y+h:g}" stroke="{stroke_attr}" stroke-width="{sw:g}"/>'
        )
    if kind == "document":
        wy = min(10.0, h * 0.15)
        by = y + h - wy
        d = (f"M {x:g},{y:g} H {x+w:g} V {by:g} "
             f"Q {x+w*0.75:g},{by-wy*1.2:g} {cx:g},{by:g} "
             f"T {x:g},{by:g} Z")
        return f'<path d="{d}" {common}/>'
    if kind == "multi_document":
        parts = []
        for ox, oy in ((8, -6), (4, -3)):
            parts.append(f'<rect x="{x+ox:g}" y="{y+oy:g}" width="{w-8:g}" height="{h-8:g}" rx="2" {common}/>')
        wy = min(9.0, (h - 6) * 0.14)
        fw, fh = w - 8, h - 6
        by = y + fh - wy
        d = (f"M {x:g},{y:g} H {x+fw:g} V {by:g} "
             f"Q {x+fw*0.75:g},{by-wy*1.1:g} {x+fw*0.5:g},{by:g} "
             f"T {x:g},{by:g} Z")
        parts.append(f'<path d="{d}" {common}/>')
        return "".join(parts)
    if kind == "cylinder":
        ry = min(11.0, h * 0.16)
        d_body = (f"M {x:g},{y+ry:g} V {y+h-ry:g} "
                  f"A {w/2:g},{ry:g} 0 0,0 {x+w:g},{y+h-ry:g} "
                  f"V {y+ry:g} A {w/2:g},{ry:g} 0 0,0 {x:g},{y+ry:g} Z")
        d_top = f"M {x:g},{y+ry:g} A {w/2:g},{ry:g} 0 0,0 {x+w:g},{y+ry:g}"
        return (f'<path d="{d_body}" {common}/>'
                f'<ellipse cx="{cx:g}" cy="{y+ry:g}" rx="{w/2:g}" ry="{ry:g}" {common}/>'
                f'<path d="{d_top}" fill="none" stroke="{stroke_attr}" stroke-width="{sw:g}"/>')
    if kind == "direct_data":
        rx = min(12.0, w * 0.12)
        d = (f"M {x+rx:g},{y:g} H {x+w-rx:g} A {rx:g},{h/2:g} 0 0,1 {x+w-rx:g},{y+h:g} "
             f"H {x+rx:g} A {rx:g},{h/2:g} 0 0,1 {x+rx:g},{y:g} Z")
        return (f'<path d="{d}" {common}/>'
                f'<ellipse cx="{x+w-rx:g}" cy="{cy:g}" rx="{rx:g}" ry="{h/2:g}" {common}/>')
    if kind == "stored_data":
        c = min(18.0, w * 0.14)
        d = (f"M {x+c:g},{y:g} H {x+w:g} Q {x+w-c*1.2:g},{cy:g} {x+w:g},{y+h:g} "
             f"H {x+c:g} Q {x-c*0.6:g},{cy:g} {x+c:g},{y:g} Z")
        return f'<path d="{d}" {common}/>'
    if kind == "sequential_data":
        r = min(w, h) / 2.0 - 2
        return (f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" {common}/>'
                f'<line x1="{cx:g}" y1="{cy+r:g}" x2="{x+w:g}" y2="{cy+r:g}" stroke="{stroke_attr}" stroke-width="{sw:g}"/>')
    if kind == "internal_storage":
        return (f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="2" {common}/>'
                f'<line x1="{x+14:g}" y1="{y:g}" x2="{x+14:g}" y2="{y+h:g}" stroke="{stroke_attr}" stroke-width="{sw:g}"/>'
                f'<line x1="{x:g}" y1="{y+14:g}" x2="{x+w:g}" y2="{y+14:g}" stroke="{stroke_attr}" stroke-width="{sw:g}"/>')
    if kind == "card":
        cut = min(float(st.get("size", 18) or 18), w * 0.25, h * 0.45)
        pts = f"{x+cut:g},{y:g} {x+w:g},{y:g} {x+w:g},{y+h:g} {x:g},{y+h:g} {x:g},{y+cut:g}"
        return f'<polygon points="{pts}" {common}/>'
    if kind == "paper_tape":
        wy = min(10.0, h * 0.16)
        ty_w = y + wy
        by_w = y + h - wy
        d = (
            f"M {x:g},{ty_w:g} "
            f"Q {x+w*0.25:g},{ty_w+wy*1.2:g} {cx:g},{ty_w:g} "
            f"T {x+w:g},{ty_w:g} "
            f"V {by_w:g} "
            f"Q {x+w*0.75:g},{by_w-wy*1.2:g} {cx:g},{by_w:g} "
            f"T {x:g},{by_w:g} Z"
        )
        return f'<path d="{d}" {common}/>'
    if kind == "hexagon":
        dx = min(22.0, w * 0.15)
        pts = f"{x+dx:g},{y:g} {x+w-dx:g},{y:g} {x+w:g},{cy:g} {x+w-dx:g},{y+h:g} {x+dx:g},{y+h:g} {x:g},{cy:g}"
        return f'<polygon points="{pts}" {common}/>'
    if kind == "manual_op":
        dx = min(22.0, w * 0.15)
        pts = f"{x:g},{y:g} {x+w:g},{y:g} {x+w-dx:g},{y+h:g} {x+dx:g},{y+h:g}"
        return f'<polygon points="{pts}" {common}/>'
    if kind == "trapezoid":
        dx = min(22.0, w * 0.15)
        pts = f"{x+dx:g},{y:g} {x+w-dx:g},{y:g} {x+w:g},{y+h:g} {x:g},{y+h:g}"
        return f'<polygon points="{pts}" {common}/>'
    if kind == "manual_input":
        sl = min(16.0, h * 0.25)
        pts = f"{x:g},{y+sl:g} {x+w:g},{y:g} {x+w:g},{y+h:g} {x:g},{y+h:g}"
        return f'<polygon points="{pts}" {common}/>'
    if kind == "circle":
        r = min(w, h) / 2.0
        return f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" {common}/>'
    if kind == "off_page":
        ym = y + h * 0.68
        pts = f"{x:g},{y:g} {x+w:g},{y:g} {x+w:g},{ym:g} {cx:g},{y+h:g} {x:g},{ym:g}"
        return f'<polygon points="{pts}" {common}/>'
    if kind == "loop_start":
        dx, dy = min(18.0, w * 0.14), min(16.0, h * 0.28)
        pts = f"{x+dx:g},{y:g} {x+w-dx:g},{y:g} {x+w:g},{y+dy:g} {x+w:g},{y+h:g} {x:g},{y+h:g} {x:g},{y+dy:g}"
        return f'<polygon points="{pts}" {common}/>'
    if kind == "loop_end":
        dx, dy = min(18.0, w * 0.14), min(16.0, h * 0.28)
        pts = f"{x:g},{y:g} {x+w:g},{y:g} {x+w:g},{y+h-dy:g} {x+w-dx:g},{y+h:g} {x+dx:g},{y+h:g} {x:g},{y+h-dy:g}"
        return f'<polygon points="{pts}" {common}/>'
    if kind == "delay":
        r = min(w * 0.35, h / 2.0)
        d = f"M {x:g},{y:g} H {x+w-r:g} A {r:g},{h/2:g} 0 0,1 {x+w-r:g},{y+h:g} H {x:g} Z"
        return f'<path d="{d}" {common}/>'
    if kind == "display":
        dx = min(22.0, w * 0.16)
        r = min(20.0, w * 0.16)
        d = f"M {x+dx:g},{y:g} H {x+w-r:g} Q {x+w+r*0.35:g},{cy:g} {x+w-r:g},{y+h:g} H {x+dx:g} L {x:g},{cy:g} Z"
        return f'<path d="{d}" {common}/>'
    if kind == "parallel_mode":
        return (
            f'<line x1="{x:g}" y1="{y+5:g}" x2="{x+w:g}" y2="{y+5:g}" stroke="{stroke_attr}" stroke-width="{max(2.0, sw):g}"/>'
            f'<line x1="{x:g}" y1="{y+h-5:g}" x2="{x+w:g}" y2="{y+h-5:g}" stroke="{stroke_attr}" stroke-width="{max(2.0, sw):g}"/>'
        )
    if kind == "annotation":
        bw = min(14.0, w * 0.12)
        if st.get("flipH") == "1":
            d = f"M {x+w-bw:g},{y:g} H {x+w:g} V {y+h:g} H {x+w-bw:g}"
        else:
            d = f"M {x+bw:g},{y:g} H {x:g} V {y+h:g} H {x+bw:g}"
        return f'<path d="{d}" fill="none" stroke="{stroke_attr}" stroke-width="{sw:g}"/>'
    if kind == "ellipsis":
        dot_col = _esc_attr(st.get("fontColor", "#1C2327"))
        dot_y = cy
        r = 3.2
        return (
            f'<circle cx="{cx-14:g}" cy="{dot_y:g}" r="{r:g}" fill="{dot_col}"/>'
            f'<circle cx="{cx:g}" cy="{dot_y:g}" r="{r:g}" fill="{dot_col}"/>'
            f'<circle cx="{cx+14:g}" cy="{dot_y:g}" r="{r:g}" fill="{dot_col}"/>'
        )
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" {common}/>'


def _render_overlay_multi_doc(x, y, w, h, st, items, base_fsize, base_fcol):
    """Render ISO 5807:1985 §10.3.2 stacked document symbols with per-layer labels."""
    fill = st.get("fillColor", "#FFFFFF")
    fill_attr = "none" if fill == "none" else _esc_attr(fill)
    stroke = st.get("strokeColor", "#4A5860")
    stroke_attr = "none" if stroke == "none" else _esc_attr(stroke)
    sw = float(st.get("strokeWidth", 1.5) or 1.5)
    common = f'fill="{fill_attr}" stroke="{stroke_attr}" stroke-width="{sw:g}" stroke-linejoin="round"'
    fcol_attr = _esc_attr(base_fcol)
    n = len(items)
    if n <= 1:
        return _render_shape_svg("multi_document", x, y, w, h, st)

    step_x = min(14.0, max(6.0, (w - 90.0) / max(1, n - 1)))
    step_y = min(24.0, max(16.0, (h - 48.0) / max(1, n - 1)))
    card_w = max(70.0, w - step_x * (n - 1))
    card_h = max(44.0, h - step_y * (n - 1))
    wy = min(8.0, card_h * 0.14)
    fs_strip = max(10, min(base_fsize, 11))

    parts = []
    # Draw back-to-front so each sheet's top strip remains visible and readable top-to-bottom
    for i, item_txt in enumerate(items):
        cx_i = x + (n - 1 - i) * step_x
        cy_i = y + i * step_y
        by_i = cy_i + card_h - wy
        d = (
            f"M {cx_i:g},{cy_i:g} H {cx_i+card_w:g} V {by_i:g} "
            f"Q {cx_i+card_w*0.75:g},{by_i-wy*1.1:g} {cx_i+card_w*0.5:g},{by_i:g} "
            f"T {cx_i:g},{by_i:g} Z"
        )
        parts.append(f'<path d="{d}" {common}/>')
        if i < n - 1:
            ty = cy_i + step_y * 0.66
            parts.append(
                f'<text x="{cx_i + card_w / 2.0:g}" y="{ty:g}" text-anchor="middle" '
                f'font-size="{fs_strip}" font-weight="600" fill="{fcol_attr}">'
                f'{html.escape(item_txt)}</text>'
            )
        else:
            ty = cy_i + (card_h - wy) / 2.0 + base_fsize * 0.36
            parts.append(
                f'<text x="{cx_i + card_w / 2.0:g}" y="{ty:g}" text-anchor="middle" '
                f'font-size="{base_fsize}" font-weight="600" fill="{fcol_attr}">'
                f'{html.escape(item_txt)}</text>'
            )
    return "".join(parts)


def _rounded_polyline_d(pts, radius=6.0):
    if len(pts) < 2:
        return ""
    # Deduplicate consecutive identical points
    clean = [pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0] - clean[-1][0], p[1] - clean[-1][1]) > 0.5:
            clean.append(p)
    if len(clean) < 2:
        return ""
    if len(clean) == 2:
        return f"M {clean[0][0]:g},{clean[0][1]:g} L {clean[1][0]:g},{clean[1][1]:g}"

    parts = [f"M {clean[0][0]:g},{clean[0][1]:g}"]
    for i in range(1, len(clean) - 1):
        p0, p1, p2 = clean[i - 1], clean[i], clean[i + 1]
        v1 = (p1[0] - p0[0], p1[1] - p0[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1 = math.hypot(*v1)
        l2 = math.hypot(*v2)
        if l1 < 1.0 or l2 < 1.0:
            parts.append(f"L {p1[0]:g},{p1[1]:g}")
            continue
        r = min(radius, l1 * 0.45, l2 * 0.45)
        a = (p1[0] - v1[0] / l1 * r, p1[1] - v1[1] / l1 * r)
        b = (p1[0] + v2[0] / l2 * r, p1[1] + v2[1] / l2 * r)
        parts.append(f"L {a[0]:g},{a[1]:g} Q {p1[0]:g},{p1[1]:g} {b[0]:g},{b[1]:g}")
    parts.append(f"L {clean[-1][0]:g},{clean[-1][1]:g}")
    return " ".join(parts)


def _longest_segment(pts):
    """Return (index, a, b, length) of the longest segment in pts."""
    best = (0, pts[0], pts[-1], 0.0)
    for idx, (a, b) in enumerate(zip(pts, pts[1:])):
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        if ln > best[3]:
            best = (idx, a, b, ln)
    return best


def _communication_link_d(pts):
    """Build SVG path with ISO 5807:1985 §9.3.2.2 lightning/zigzag kink on longest segment."""
    if len(pts) < 2:
        return ""
    idx, a, b, ln = _longest_segment(pts)
    if ln < 32.0:
        return _rounded_polyline_d(pts, radius=6.0)
    ux, uy = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
    px, py = -uy, ux
    mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    span = min(12.0, ln * 0.16)
    amp = 7.0
    p_pre = (mx - ux * span, my - uy * span)
    p_z1 = (mx - ux * (span * 0.25) + px * amp, my - uy * (span * 0.25) + py * amp)
    p_z2 = (mx + ux * (span * 0.25) - px * amp, my + uy * (span * 0.25) - py * amp)
    p_post = (mx + ux * span, my + uy * span)
    new_pts = list(pts[:idx + 1]) + [p_pre, p_z1, p_z2, p_post] + list(pts[idx + 1:])
    return _rounded_polyline_d(new_pts, radius=2.5)


def _control_transfer_svg(pts, code_txt, stroke, bg_fill, sw):
    """Render ISO 5807:1985 §9.3.2.1 control transfer triangle marker (P, T, I, etc.)."""
    if len(pts) < 2:
        return "", False
    _, a, b, ln = _longest_segment(pts)
    if ln < 12.0:
        return "", False
    ux, uy = (b[0] - a[0]) / ln, (b[1] - a[1]) / ln
    px, py = -uy, ux
    mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
    tip = (mx + ux * 13.0, my + uy * 13.0)
    base_c = (mx - ux * 11.0, my - uy * 11.0)
    b1 = (base_c[0] + px * 12.0, base_c[1] + py * 12.0)
    b2 = (base_c[0] - px * 12.0, base_c[1] - py * 12.0)
    tri_pts = f"{tip[0]:g},{tip[1]:g} {b1[0]:g},{b1[1]:g} {b2[0]:g},{b2[1]:g}"
    clean_code = (code_txt or "").strip()
    inside_code = bool(clean_code and len(clean_code) <= 3)
    code_svg = ""
    if inside_code:
        tx = mx - ux * 2.5
        ty = my - uy * 2.5 + 3.6
        code_svg = (
            f'<text x="{tx:g}" y="{ty:g}" text-anchor="middle" font-size="10" '
            f'font-weight="700" fill="{stroke}">{html.escape(clean_code)}</text>'
        )
    marker = (
        f'<g class="control-transfer-marker" data-code="{_esc_attr(clean_code)}">'
        f'<polygon points="{tri_pts}" fill="{bg_fill}" stroke="{stroke}" stroke-width="{sw:g}" stroke-linejoin="round"/>'
        f'{code_svg}</g>'
    )
    return marker, inside_code


def _auto_orthogonal_points(p1, p2, ex_x, ex_y, en_x, en_y):
    x1, y1 = p1
    x2, y2 = p2
    if abs(x1 - x2) < 2.0 or abs(y1 - y2) < 2.0:
        return [p1, p2]
    # Exit vertical, enter vertical
    if (ex_y in (0.0, 1.0)) and (en_y in (0.0, 1.0)):
        ym = (y1 + y2) / 2.0
        return [p1, (x1, ym), (x2, ym), p2]
    # Exit horizontal, enter vertical
    if (ex_x in (0.0, 1.0)) and (en_y in (0.0, 1.0)):
        return [p1, (x2, y1), p2]
    # Exit vertical, enter horizontal
    if (ex_y in (0.0, 1.0)) and (en_x in (0.0, 1.0)):
        return [p1, (x1, y2), p2]
    xm = (x1 + x2) / 2.0
    return [p1, (xm, y1), (xm, y2), p2]


def _arrow_polygon(p_prev, p_tip, size=8.0):
    dx, dy = p_tip[0] - p_prev[0], p_tip[1] - p_prev[1]
    ln = math.hypot(dx, dy)
    if ln < 0.5:
        return ""
    ux, uy = dx / ln, dy / ln
    bx, by = p_tip[0] - ux * size, p_tip[1] - uy * size
    px, py = -uy * (size * 0.52), ux * (size * 0.52)
    return f"{p_tip[0]:g},{p_tip[1]:g} {bx+px:g},{by+py:g} {bx-px:g},{by-py:g}"


def render_page_svg(page_el):
    """Render one <diagram> element to a standalone SVG string."""
    model = page_el.find("mxGraphModel")
    root = model.find("root") if model is not None else None
    if root is None:
        return ""

    bg = model.get("background") or "#F8F6F2"
    raw_cells = []
    for child in root:
        if child.tag == "mxCell":
            raw_cells.append(child)
        elif child.tag in ("UserObject", "object"):
            inner = child.find("mxCell")
            if inner is not None:
                cp = ET.Element("mxCell", dict(inner.attrib))
                cp.set("id", child.get("id", inner.get("id", "")))
                cp.set("value", child.get("label") or child.get("value") or inner.get("value", ""))
                for sub in inner:
                    cp.append(sub)
                raw_cells.append(cp)

    by_id = {c.get("id"): c for c in raw_cells if c.get("id")}
    child_edge_labels = {}
    for c in raw_cells:
        st_str = c.get("style") or ""
        g = c.find("mxGeometry")
        if "edgeLabel" in st_str or (g is not None and g.get("relative") == "1" and c.get("vertex") == "1"):
            pid = c.get("parent")
            if pid and c.get("value"):
                child_edge_labels[pid] = c.get("value")

    def get_origin(cell):
        dx = dy = 0.0
        pid = cell.get("parent")
        seen = set()
        while pid and pid in by_id and pid not in seen:
            seen.add(pid)
            p = by_id[pid]
            if p.get("vertex") == "1":
                pg = p.find("mxGeometry")
                if pg is not None:
                    dx += float(pg.get("x", 0) or 0)
                    dy += float(pg.get("y", 0) or 0)
            pid = p.get("parent")
        return dx, dy

    vertices = []
    swimlanes = []
    edges = []
    max_x, max_y = 600.0, 400.0

    for c in raw_cells:
        cid = c.get("id")
        if cid in ("0", "1", None):
            continue
        st = _parse_style(c.get("style") or "")
        if c.get("edge") == "1":
            edges.append((c, st))
            continue
        if c.get("vertex") == "1":
            g = c.find("mxGeometry")
            if g is None or g.get("relative") == "1" or "edgeLabel" in (c.get("style") or ""):
                continue
            dx, dy = get_origin(c)
            x = dx + float(g.get("x", 0) or 0)
            y = dy + float(g.get("y", 0) or 0)
            w = float(g.get("width", 120) or 120)
            h = float(g.get("height", 60) or 60)
            max_x = max(max_x, x + w + 60)
            max_y = max(max_y, y + h + 50)
            kind = _detect_shape(st)
            if kind == "swimlane":
                swimlanes.append((cid, c, st, x, y, w, h))
            else:
                vertices.append((cid, c, st, kind, x, y, w, h))

    abs_box = {cid: (x, y, w, h) for cid, _, _, _, x, y, w, h in vertices}
    for cid, _, _, x, y, w, h in swimlanes:
        abs_box[cid] = (x, y, w, h)

    # Pre-resolve edge routes so viewBox encloses outer corridors
    resolved_edges = []
    for c, st in edges:
        eid = c.get("id") or ""
        src, tgt = c.get("source"), c.get("target")
        if src not in abs_box or tgt not in abs_box:
            continue
        sx, sy, sw_b, sh_b = abs_box[src]
        tx, ty, tw_b, th_b = abs_box[tgt]
        ex_x = float(st.get("exitX", 0.5)) if "exitX" in st else None
        ex_y = float(st.get("exitY", 1.0)) if "exitY" in st else None
        en_x = float(st.get("entryX", 0.5)) if "entryX" in st else None
        en_y = float(st.get("entryY", 0.0)) if "entryY" in st else None

        if ex_x is None or ex_y is None:
            scx, scy = sx + sw_b / 2, sy + sh_b / 2
            tcx, tcy = tx + tw_b / 2, ty + th_b / 2
            if abs(tcy - scy) >= abs(tcx - scx):
                ex_x, ex_y = 0.5, (1.0 if tcy >= scy else 0.0)
            else:
                ex_x, ex_y = (1.0 if tcx >= scx else 0.0), 0.5
        if en_x is None or en_y is None:
            scx, scy = sx + sw_b / 2, sy + sh_b / 2
            tcx, tcy = tx + tw_b / 2, ty + th_b / 2
            if abs(tcy - scy) >= abs(tcx - scx):
                en_x, en_y = 0.5, (0.0 if tcy >= scy else 1.0)
            else:
                en_x, en_y = (0.0 if tcx >= scx else 1.0), 0.5

        p_start = (sx + ex_x * sw_b, sy + ex_y * sh_b)
        p_end = (tx + en_x * tw_b, ty + en_y * th_b)

        g = c.find("mxGeometry")
        arr = g.find("Array") if g is not None else None
        edx, edy = get_origin(c)
        wps = []
        if arr is not None:
            for pt in arr.findall("mxPoint"):
                if pt.get("x") is not None and pt.get("y") is not None:
                    wx = edx + float(pt.get("x"))
                    wy = edy + float(pt.get("y"))
                    wps.append((wx, wy))
                    max_x = max(max_x, wx + 60)
                    max_y = max(max_y, wy + 50)

        raw_pts = ([p_start] + wps + [p_end]) if wps else _auto_orthogonal_points(p_start, p_end, ex_x, ex_y, en_x, en_y)
        pts = [raw_pts[0]]
        for p_cur in raw_pts[1:]:
            if math.hypot(p_cur[0] - pts[-1][0], p_cur[1] - pts[-1][1]) > 0.5:
                pts.append(p_cur)
        lbl_raw = c.get("value") or child_edge_labels.get(eid, "")
        resolved_edges.append((eid, st, pts, lbl_raw))

    # Trim excess blank page space while keeping clean 40px breathing room
    vw = max(480, int(math.ceil(max_x)))
    vh = max(320, int(math.ceil(max_y)))

    bg_esc = _esc_attr(bg)
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" width="{vw}" height="{vh}" role="img" aria-label="{_esc_attr(page_el.get("name") or "Diagram")}">',
        f'<defs><style>{GOOGLE_FONTS_IMPORT}'
        f' text {{ font-family: "Open Sans", "Segoe UI", Roboto, Arial, sans-serif; }}'
        f'</style></defs>',
        f'<rect x="0" y="0" width="{vw}" height="{vh}" fill="{bg_esc}"/>',
    ]

    # 1. Render Swimlanes & Pools (outermost first)
    for cid, c, st, x, y, w, h in swimlanes:
        hdr_size = float(st.get("startSize", 36) or 36)
        horiz = st.get("horizontal", "1") != "0"
        hdr_fill = _esc_attr(st.get("fillColor", "#E8ECEF"))
        body_fill_raw = st.get("swimlaneFillColor", "none")
        body_fill = _esc_attr(body_fill_raw)
        stroke = _esc_attr(st.get("strokeColor", "#4A5860"))
        fcol = _esc_attr(st.get("fontColor", "#1C2327"))
        fsize = int(float(st.get("fontSize", 13) or 13))
        sw = float(st.get("strokeWidth", 1.5) or 1.5)
        lbl_lines = _strip_html_lines(c.get("value"))
        lbl_txt = " ".join(l["text"] for l in lbl_lines)

        g_chunk = [f'<g data-cell-id="{_esc_attr(cid)}" data-shape="swimlane">']
        if body_fill_raw and body_fill_raw != "none":
            g_chunk.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{body_fill}" stroke="none"/>')
        if horiz:
            g_chunk.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{hdr_size:g}" fill="{hdr_fill}" stroke="{stroke}" stroke-width="{sw:g}"/>')
            g_chunk.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="none" stroke="{stroke}" stroke-width="{sw:g}"/>')
            if lbl_txt:
                g_chunk.append(
                    f'<text x="{x+w/2:g}" y="{y+hdr_size/2+fsize*0.36:g}" text-anchor="middle" '
                    f'font-size="{fsize}" font-weight="700" fill="{fcol}">{html.escape(lbl_txt)}</text>'
                )
        else:
            g_chunk.append(f'<rect x="{x:g}" y="{y:g}" width="{hdr_size:g}" height="{h:g}" fill="{hdr_fill}" stroke="{stroke}" stroke-width="{sw:g}"/>')
            g_chunk.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="none" stroke="{stroke}" stroke-width="{sw:g}"/>')
            if lbl_txt:
                tx, ty = x + hdr_size / 2.0 + fsize * 0.35, y + h / 2.0
                g_chunk.append(
                    f'<text x="{tx:g}" y="{ty:g}" text-anchor="middle" transform="rotate(-90 {tx:g} {ty:g})" '
                    f'font-size="{fsize}" font-weight="700" fill="{fcol}">{html.escape(lbl_txt)}</text>'
                )
        g_chunk.append("</g>")
        svg_parts.append("".join(g_chunk))

    # 2. Render Edges (supports startArrow + endArrow, control_transfer §9.3.2.1, communication_link §9.3.2.2)
    edge_labels_deferred = []
    for eid, st, pts, lbl_raw in resolved_edges:
        stroke_raw = st.get("strokeColor", "#2B373E")
        stroke = _esc_attr(stroke_raw)
        sw = float(st.get("strokeWidth", 1.5) or 1.5)
        dash = ' stroke-dasharray="5,4"' if st.get("dashed") == "1" else ""
        iso_line = (st.get("isoLine") or "").strip().lower()
        if iso_line == "communication_link":
            d = _communication_link_d(pts)
        else:
            d = _rounded_polyline_d(pts, radius=6.0)
        if not d:
            continue

        start_arrow = (st.get("startArrow") or "none").strip()
        end_arrow = (st.get("endArrow") or "block").strip()
        start_fill = st.get("startFill", "1")
        end_fill = st.get("endFill", "1")
        arrow_size = max(7.5, sw * 4.6)

        arrow_parts = []
        if start_arrow and start_arrow.lower() != "none" and len(pts) >= 2:
            apts_s = _arrow_polygon(pts[1], pts[0], size=arrow_size)
            if apts_s:
                afill = "none" if (start_fill == "0" or start_arrow.lower() == "open") else stroke
                astrk = f' stroke="{stroke}" stroke-width="{sw:g}"' if afill == "none" else ""
                arrow_parts.append(f'<polygon class="arrow-start" points="{apts_s}" fill="{afill}"{astrk}/>')
        if end_arrow and end_arrow.lower() != "none" and len(pts) >= 2:
            apts_e = _arrow_polygon(pts[-2], pts[-1], size=arrow_size)
            if apts_e:
                afill = "none" if (end_fill == "0" or end_arrow.lower() == "open") else stroke
                astrk = f' stroke="{stroke}" stroke-width="{sw:g}"' if afill == "none" else ""
                arrow_parts.append(f'<polygon class="arrow-end" points="{apts_e}" fill="{afill}"{astrk}/>')

        lbl_lines = _strip_html_lines(lbl_raw)
        lbl_txt = " ".join(l["text"] for l in lbl_lines) if lbl_lines else ""

        marker_svg = ""
        consumed_label = False
        if iso_line == "control_transfer":
            marker_svg, consumed_label = _control_transfer_svg(pts, lbl_txt, stroke, bg_esc, sw)

        line_attr = f' data-iso-line="{_esc_attr(iso_line)}"' if iso_line else ""
        svg_parts.append(
            f'<g data-cell-id="{_esc_attr(eid)}" data-edge="1" '
            f'data-start-arrow="{_esc_attr(start_arrow)}" data-end-arrow="{_esc_attr(end_arrow)}"{line_attr}>'
            f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw:g}" stroke-linecap="round"{dash}/>'
            f'{"".join(arrow_parts)}{marker_svg}</g>'
        )

        if lbl_txt and not consumed_label:
            seg_x, seg_y = (pts[0][0] + pts[-1][0]) / 2.0, (pts[0][1] + pts[-1][1]) / 2.0
            if st.get("isoStemBranch") == "1" and len(pts) >= 3:
                # Place branch label cleanly on the individual target drop leg (ISO §10.3.1(b))
                a_pt, b_pt = pts[-2], pts[-1]
                seg_x = a_pt[0] + (b_pt[0] - a_pt[0]) * 0.48
                seg_y = a_pt[1] + (b_pt[1] - a_pt[1]) * 0.48
            else:
                # Place label along first non-tiny segment (ideal for Decision exits!)
                for a_pt, b_pt in zip(pts, pts[1:]):
                    slen = math.hypot(b_pt[0] - a_pt[0], b_pt[1] - a_pt[1])
                    if slen >= 28:
                        t = 0.44 if len(pts) == 2 else 0.5
                        seg_x = a_pt[0] + (b_pt[0] - a_pt[0]) * t
                        seg_y = a_pt[1] + (b_pt[1] - a_pt[1]) * t
                        break
            lbg = st.get("labelBackgroundColor", bg)
            if lbg == "none":
                lbg = bg
            lcol = st.get("fontColor", stroke_raw)
            edge_labels_deferred.append((seg_x, seg_y, lbl_txt, _esc_attr(lbg), _esc_attr(lcol)))

    # 3. Render Vertices & Multi-line Vietnamese Text
    for cid, c, st, kind, x, y, w, h in vertices:
        base_fsize = int(float(st.get("fontSize", 12) or 12))
        base_fcol = st.get("fontColor", "#1C2327")
        is_bold_style = st.get("fontStyle") in ("1", "3")
        align = st.get("align", "left" if kind in ("annotation", "text") else "center")

        overlay_items = _parse_overlay_items(st)
        extra_g_attrs = f' data-shape="{_esc_attr(kind)}"'

        if kind == "multi_document" and overlay_items and len(overlay_items) > 1:
            shape_svg = _render_overlay_multi_doc(x, y, w, h, st, overlay_items, base_fsize, base_fcol)
            extra_g_attrs += f' data-overlay-items="{_esc_attr(json.dumps(overlay_items, ensure_ascii=False))}"'
            svg_parts.append(f'<g data-cell-id="{_esc_attr(cid)}"{extra_g_attrs}>{shape_svg}</g>')
            continue

        rich = _strip_html_lines(c.get("value"))
        plain_joined = " ".join(r["text"] for r in rich).strip()

        if kind == "ellipsis":
            has_caption = bool(plain_joined and plain_joined not in ("...", "…"))
            dot_col = _esc_attr(base_fcol)
            dot_y = y + (h * 0.34 if has_caption else h * 0.5)
            cx_e = x + w / 2.0
            shape_svg = (
                f'<circle cx="{cx_e-14:g}" cy="{dot_y:g}" r="3.2" fill="{dot_col}"/>'
                f'<circle cx="{cx_e:g}" cy="{dot_y:g}" r="3.2" fill="{dot_col}"/>'
                f'<circle cx="{cx_e+14:g}" cy="{dot_y:g}" r="3.2" fill="{dot_col}"/>'
            )
            text_svg = ""
            if has_caption:
                text_svg = (
                    f'<text x="{cx_e:g}" y="{y + h * 0.78:g}" text-anchor="middle" '
                    f'font-size="11" font-weight="600" fill="{dot_col}">{html.escape(plain_joined)}</text>'
                )
            svg_parts.append(f'<g data-cell-id="{_esc_attr(cid)}"{extra_g_attrs}>{shape_svg}{text_svg}</g>')
            continue

        shape_svg = _render_shape_svg(kind, x, y, w, h, st)
        wrapped = _wrap_rich_lines(rich, w, base_fsize, kind) if kind != "text" else rich

        text_svg = ""
        if wrapped:
            line_heights = [(item["font_size"] or base_fsize) * 1.38 for item in wrapped]
            tot_th = sum(line_heights)
            cy_shift = y + (h * 0.56 if kind == "cylinder" else h * 0.5)
            first_fs = wrapped[0]["font_size"] or base_fsize
            cur_ty = cy_shift - tot_th / 2.0 + first_fs * 0.88

            if align == "left":
                tx = x + ((6 if st.get("flipH") == "1" else 16) if kind == "annotation" else 4)
                anchor = "start"
            elif align == "right":
                tx = x + w - 8
                anchor = "end"
            else:
                tx = x + w / 2.0
                anchor = "middle"

            tspans = []
            for idx, item in enumerate(wrapped):
                dy_val = 0 if idx == 0 else line_heights[idx]
                fw = "700" if (item["bold"] or is_bold_style) else "400"
                fc = _esc_attr(item["color"] or base_fcol)
                fs = item["font_size"] or base_fsize
                if idx == 0:
                    tspans.append(
                        f'<tspan x="{tx:g}" y="{cur_ty:g}" font-size="{fs}" font-weight="{fw}" fill="{fc}">'
                        f'{html.escape(item["text"])}</tspan>'
                    )
                else:
                    tspans.append(
                        f'<tspan x="{tx:g}" dy="{dy_val:g}" font-size="{fs}" font-weight="{fw}" fill="{fc}">'
                        f'{html.escape(item["text"])}</tspan>'
                    )
            text_svg = f'<text text-anchor="{anchor}">{"".join(tspans)}</text>'

        svg_parts.append(f'<g data-cell-id="{_esc_attr(cid)}"{extra_g_attrs}>{shape_svg}{text_svg}</g>')

    # 4. Render Edge Label Pills on top so lines never strike through Vietnamese text
    for lx, ly, ltxt, lbg, lcol in edge_labels_deferred:
        pw_pill = max(28.0, len(ltxt) * 6.7 + 12.0)
        ph_pill = 19.0
        svg_parts.append(
            f'<g class="edge-label">'
            f'<rect x="{lx - pw_pill/2:g}" y="{ly - ph_pill/2:g}" width="{pw_pill:g}" height="{ph_pill:g}" '
            f'rx="4" fill="{lbg}" stroke="none" opacity="0.94"/>'
            f'<text x="{lx:g}" y="{ly + 3.8:g}" text-anchor="middle" font-size="11" font-weight="600" fill="{lcol}">'
            f'{html.escape(ltxt)}</text></g>'
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def render_drawio_pages_to_svgs(root_el):
    pages = root_el.findall("diagram") or [root_el]
    out = []
    for i, pg in enumerate(pages):
        pid = pg.get("id") or f"p{i+1}"
        pname = pg.get("name") or f"Page {i+1}"
        svg = render_page_svg(pg)
        if svg:
            out.append(((pid, pname), svg))
    return out


def _extract_model_bg_hex(root_el):
    pages = root_el.findall("diagram") or [root_el]
    for pg in pages:
        model = pg.find("mxGraphModel")
        if model is not None:
            raw = (model.get("background") or "").strip().lstrip("#")
            if re.fullmatch(r"[0-9A-Fa-f]{6}", raw):
                return raw.lower()
    return "f8f6f2"


def render_drawio_file(drawio_path, out_svg=None, out_html=None, out_png=None):
    tree = ET.parse(drawio_path)
    root_el = tree.getroot()
    rendered = render_drawio_pages_to_svgs(root_el)
    if not rendered:
        raise RuntimeError(f"No diagram pages rendered from {drawio_path}")

    if out_svg:
        os.makedirs(os.path.dirname(os.path.abspath(out_svg)), exist_ok=True)
        with open(out_svg, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + rendered[0][1] + "\n")
        sys.stderr.write(f"wrote {out_svg}\n")

    if out_html:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import drawiohtml
        meta = [m for m, _ in rendered]
        svgs = [s for _, s in rendered]
        title = os.path.splitext(os.path.basename(drawio_path))[0]
        os.makedirs(os.path.dirname(os.path.abspath(out_html)), exist_ok=True)
        with open(out_html, "w", encoding="utf-8") as f:
            f.write(drawiohtml.build_html(title, meta, svgs))
        sys.stderr.write(f"wrote {out_html}\n")

    if out_png:
        chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
        if not chrome:
            raise RuntimeError(
                "Chrome/Chromium binary not found on PATH; cannot render PNG "
                "(SVG/HTML rendering works without Chrome)."
            )
        m_wh = re.search(r'viewBox="0 0 (\d+) (\d+)"', rendered[0][1])
        w = int(m_wh.group(1)) + 40 if m_wh else 1280
        h = int(m_wh.group(2)) + 40 if m_wh else 900
        bg_hex = _extract_model_bg_hex(root_el)
        os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
        if out_svg:
            subprocess.run([
                chrome, "--headless", "--no-sandbox", "--disable-gpu",
                f"--window-size={w},{h}", f"--default-background-color={bg_hex}",
                f"--screenshot={os.path.abspath(out_png)}",
                f"file://{os.path.abspath(out_svg)}"
            ], check=True, capture_output=True)
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_svg = os.path.join(tmpdir, "render.svg")
                with open(tmp_svg, "w", encoding="utf-8") as f:
                    f.write(rendered[0][1])
                subprocess.run([
                    chrome, "--headless", "--no-sandbox", "--disable-gpu",
                    f"--window-size={w},{h}", f"--default-background-color={bg_hex}",
                    f"--screenshot={os.path.abspath(out_png)}",
                    f"file://{os.path.abspath(tmp_svg)}"
                ], check=True, capture_output=True)
        sys.stderr.write(f"wrote {out_png}\n")


def main():
    ap = argparse.ArgumentParser(description="Render a .drawio XML file to standalone SVG, HTML, and optional PNG.")
    ap.add_argument("file", help="Input .drawio file")
    ap.add_argument("-o", "--output", help="Output .svg path")
    ap.add_argument("--html", help="Optional interactive .html viewer path")
    ap.add_argument("--png", help="Optional headless Chrome .png path")
    args = ap.parse_args()

    out_svg = args.output or (os.path.splitext(args.file)[0] + ".svg" if not (args.html or args.png) else None)
    try:
        render_drawio_file(args.file, out_svg=out_svg, out_html=args.html, out_png=args.png)
    except (ET.ParseError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        sys.exit(f"error: cannot render {args.file}: {exc}")


if __name__ == "__main__":
    main()
