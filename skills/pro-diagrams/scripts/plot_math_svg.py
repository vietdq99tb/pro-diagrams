#!/usr/bin/env python3
"""Zero-dependency pure-Python SVG Mathematical Function Plotter (`y = f(x)`).

Renders single or multiple continuous/piecewise mathematical functions, asymptotes,
shaded integral regions, and labeled critical/intersection points using Open Sans,
JetBrains Mono, and the 'Atelier Technical Warm' palette — no Matplotlib required.

Usage:
  python3 plot_math_svg.py math_spec.json -o plot.svg [--html plot.html]
"""
import argparse
import ast
import html
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)

SAFE_MATH = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "exp": math.exp, "log": math.log, "ln": math.log, "log10": math.log10,
    "sqrt": math.sqrt, "abs": abs, "pi": math.pi, "e": math.e,
    "floor": math.floor, "ceil": math.ceil,
}


def _esc(val):
    return html.escape(str(val), quote=True)


def _load_theme(theme_name):
    with open(os.path.join(SKILL_DIR, "data", "theme-tokens.json"), encoding="utf-8") as f:
        themes = json.load(f)["themes"]
    if theme_name not in themes:
        raise ValueError(f"unknown theme {theme_name!r}; expected one of {', '.join(sorted(themes))}")
    return themes[theme_name]


def _compile_expr(expr_str):
    """Parse and strictly validate a math expression AST before evaluation."""
    if not isinstance(expr_str, str) or not expr_str.strip():
        raise ValueError(f"invalid expression {expr_str!r}: expression must be a non-empty string")
    try:
        tree = ast.parse(expr_str, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid expression {expr_str!r}: syntax error ({exc.msg})") from exc

    def _validate(node):
        if isinstance(node, ast.Expression):
            _validate(node.body)
            return
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return
            raise ValueError(f"invalid expression {expr_str!r}: unsupported constant {node.value!r}")
        if isinstance(node, ast.Name):
            if node.id == "x":
                return
            if node.id in SAFE_MATH and isinstance(SAFE_MATH[node.id], (int, float)):
                return
            raise ValueError(f"invalid expression {expr_str!r}: unsupported symbol {node.id!r}")
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, (ast.UAdd, ast.USub)):
                _validate(node.operand)
                return
            raise ValueError(f"invalid expression {expr_str!r}: unsupported unary operator")
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.BitXor):
                raise ValueError(
                    f"invalid expression {expr_str!r}: use '**' for exponentiation instead of '^'"
                )
            if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
                _validate(node.left)
                _validate(node.right)
                return
            raise ValueError(f"invalid expression {expr_str!r}: unsupported binary operator")
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in SAFE_MATH
                and callable(SAFE_MATH[node.func.id])
                and not node.keywords
            ):
                fname = node.func.id
                nargs = len(node.args)
                if fname in ("log", "ln"):
                    if nargs not in (1, 2):
                        raise ValueError(f"invalid expression {expr_str!r}: {fname}() takes 1 or 2 arguments")
                elif nargs != 1:
                    raise ValueError(f"invalid expression {expr_str!r}: {fname}() takes exactly 1 argument")
                for arg in node.args:
                    _validate(arg)
                return
            raise ValueError(f"invalid expression {expr_str!r}: unsupported function call")
        raise ValueError(f"invalid expression {expr_str!r}: unsupported AST construct")

    _validate(tree)
    return tree


def _eval_ast(tree, x_val):
    """Evaluate a pre-validated AST node at x = x_val."""
    def _ev(node):
        if isinstance(node, ast.Expression):
            return _ev(node.body)
        if isinstance(node, ast.Constant):
            return float(node.value)
        if isinstance(node, ast.Name):
            if node.id == "x":
                return float(x_val)
            return float(SAFE_MATH[node.id])
        if isinstance(node, ast.UnaryOp):
            v = _ev(node.operand)
            return +v if isinstance(node.op, ast.UAdd) else -v
        if isinstance(node, ast.BinOp):
            a, b = _ev(node.left), _ev(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.Div):
                return a / b
            if isinstance(node.op, ast.Pow):
                res = a ** b
                if isinstance(res, complex):
                    raise ValueError("complex power result")
                return float(res)
        if isinstance(node, ast.Call):
            args = [_ev(a) for a in node.args]
            return float(SAFE_MATH[node.func.id](*args))
        raise ValueError("unsupported AST node")

    return _ev(tree)


def _eval_expr(expr_str, x_val):
    """Safely evaluate a mathematical expression in x using AST whitelist."""
    return _eval_ast(_compile_expr(expr_str), x_val)


def _sample_segments(tree, a, b, n_steps, y_min, y_max, sx, sy):
    """Sample a pre-validated math expression across [a, b], splitting safely at singularities."""
    segments = []
    cur_seg = []
    prev_y = None
    y_span = y_max - y_min
    y_clip_limit = max(abs(y_min), abs(y_max), 1.0) * 25.0
    for i in range(n_steps + 1):
        xi = a + (b - a) * (i / n_steps)
        try:
            yi = _eval_ast(tree, xi)
            if not math.isfinite(yi) or abs(yi) > y_clip_limit:
                raise ValueError("out of bounds")
            if prev_y is not None and abs(yi - prev_y) > y_span * 1.5:
                if len(cur_seg) >= 2:
                    segments.append(cur_seg)
                cur_seg = [(xi, yi, sx(xi), sy(yi))]
            else:
                cur_seg.append((xi, yi, sx(xi), sy(yi)))
            prev_y = yi
        except (ZeroDivisionError, ValueError, OverflowError, TypeError):
            if len(cur_seg) >= 2:
                segments.append(cur_seg)
            cur_seg = []
            prev_y = None
    if len(cur_seg) >= 2:
        segments.append(cur_seg)
    return segments


def render_math_plot_svg(spec, theme_name="tech-warm-light"):
    if not isinstance(spec, dict) or not spec:
        raise ValueError("math spec must be a non-empty JSON object")

    funcs = spec.get("functions")
    if not isinstance(funcs, list) or not funcs:
        raise ValueError("math spec requires a non-empty 'functions' list")

    x_range = spec.get("x_range", [-5, 5])
    y_range = spec.get("y_range", [-4, 6])
    if not isinstance(x_range, list) or len(x_range) != 2:
        raise ValueError("'x_range' must be a 2-element [min, max] list")
    if not isinstance(y_range, list) or len(y_range) != 2:
        raise ValueError("'y_range' must be a 2-element [min, max] list")
    x_min, x_max = float(x_range[0]), float(x_range[1])
    y_min, y_max = float(y_range[0]), float(y_range[1])
    if not (math.isfinite(x_min) and math.isfinite(x_max) and x_min < x_max):
        raise ValueError(f"invalid x_range [{x_min}, {x_max}]: require finite x_min < x_max")
    if not (math.isfinite(y_min) and math.isfinite(y_max) and y_min < y_max):
        raise ValueError(f"invalid y_range [{y_min}, {y_max}]: require finite y_min < y_max")

    samples = int(spec.get("samples", 400))
    if samples < 2:
        raise ValueError("'samples' must be >= 2")

    # Pre-validate and compile ALL expressions up front so invalid expressions never fail silently
    compiled_funcs = []
    for idx, fn in enumerate(funcs):
        if not isinstance(fn, dict) or "expr" not in fn:
            raise ValueError(f"functions[{idx}] must be an object containing 'expr'")
        compiled_funcs.append((fn, _compile_expr(fn["expr"])))

    shade = spec.get("shade_area")
    compiled_shade = None
    if shade is not None:
        if not isinstance(shade, dict) or not all(k in shade for k in ("expr", "from", "to")):
            raise ValueError("'shade_area' must contain 'expr', 'from', and 'to'")
        compiled_shade = (shade, _compile_expr(shade["expr"]), float(shade["from"]), float(shade["to"]))

    compiled_asymptotes = []
    for idx, asym in enumerate(spec.get("asymptotes") or []):
        if not isinstance(asym, dict):
            raise ValueError(f"asymptotes[{idx}] must be an object")
        c_tree = _compile_expr(asym["expr"]) if "expr" in asym else None
        compiled_asymptotes.append((asym, c_tree))

    theme = _load_theme(theme_name)
    pal = theme["chart_series"]

    vw = int(spec.get("width", 860))
    vh_req = int(spec.get("height", 500))
    pad_l, pad_r, pad_b = 68, 44, 56

    # Build dedicated wrapping top legend strip so long Vietnamese labels & >=3 curves never clip or overlap plot
    legend_entries = []
    max_single_w = 0.0
    for idx, (fn, _) in enumerate(compiled_funcs):
        lbl = str(fn.get("label") or f"y = {fn['expr']}")
        col = str(fn.get("color") or pal[idx % len(pal)]["hex"])
        dashed = bool(fn.get("dashed"))
        est_w = 28.0 + len(lbl) * 7.4 + 20.0
        max_single_w = max(max_single_w, est_w)
        legend_entries.append((lbl, col, dashed, est_w))

    if max_single_w > (vw - pad_l - pad_r):
        vw = int(math.ceil(pad_l + pad_r + max_single_w + 12))

    avail_leg_w = vw - pad_l - pad_r
    legend_layout = []
    cur_x = float(pad_l)
    row = 0
    for lbl, col, dashed, est_w in legend_entries:
        if cur_x > pad_l and (cur_x - pad_l + est_w) > avail_leg_w:
            row += 1
            cur_x = float(pad_l)
        legend_layout.append((row, cur_x, lbl, col, dashed))
        cur_x += est_w
    n_leg_rows = (row + 1) if legend_layout else 0

    pad_t = 44 + n_leg_rows * 22 + 24
    vh = max(vh_req, pad_t + pad_b + 300)
    pw, ph = vw - pad_l - pad_r, vh - pad_t - pad_b

    def sx(x):
        return pad_l + ((x - x_min) / (x_max - x_min)) * pw

    def sy(y):
        return pad_t + ph - ((y - y_min) / (y_max - y_min)) * ph

    title = str(spec.get("title") or "Đồ thị Hàm số Toán học")
    x_label = str(spec.get("x_label") or "x")
    y_label = str(spec.get("y_label") or "y = f(x)")

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" width="{vw}" height="{vh}" '
        f'data-chart-type="math-plot" role="img" aria-label="{_esc(title)}">',
        '<defs>'
        '<style>@import url("https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,400;0,600;0,700;1,400'
        '&amp;family=JetBrains+Mono:wght@400;600&amp;display=swap");'
        ' text { font-family: "Open Sans", "Segoe UI", Arial, sans-serif; }</style>'
        f'<clipPath id="math-plot-clip"><rect x="{pad_l}" y="{pad_t}" width="{pw}" height="{ph}"/></clipPath>'
        '</defs>',
        f'<rect x="0" y="0" width="{vw}" height="{vh}" rx="12" fill="{_esc(theme["surface"])}"/>',
        f'<text x="{pad_l}" y="30" font-size="17" font-weight="700" fill="{_esc(theme["ink_heading"])}">{_esc(title)}</text>',
    ]

    # Render dedicated top legend strip cleanly above the plot frame
    for r_idx, lx_item, lbl, col, dashed in legend_layout:
        ly_leg = 52 + r_idx * 22
        dash_attr = ' stroke-dasharray="6,4"' if dashed else ""
        svg.append(
            f'<line x1="{lx_item:.2f}" y1="{ly_leg - 4:.2f}" x2="{lx_item + 22:.2f}" y2="{ly_leg - 4:.2f}" '
            f'stroke="{_esc(col)}" stroke-width="2.5"{dash_attr}/>'
        )
        svg.append(
            f'<text x="{lx_item + 28:.2f}" y="{ly_leg:.2f}" font-size="12" font-weight="600" '
            f'fill="{_esc(theme["ink"])}">{_esc(lbl)}</text>'
        )

    # Grid ticks
    x_step = float(spec.get("x_step") or max(0.5, round((x_max - x_min) / 8, 1)))
    y_step = float(spec.get("y_step") or max(0.5, round((y_max - y_min) / 6, 1)))

    xv = math.ceil(x_min / x_step) * x_step
    while xv <= x_max + 1e-6:
        px = sx(xv)
        svg.append(f'<line x1="{px:.2f}" y1="{pad_t}" x2="{px:.2f}" y2="{pad_t+ph}" stroke="{_esc(theme["grid_line"])}" stroke-width="1"/>')
        if abs(xv) > 1e-6 or not (y_min <= 0 <= y_max):
            lbl = f"{xv:g}"
            ay = sy(0) + 16 if (y_min <= 0 <= y_max) else pad_t + ph + 18
            ay = min(pad_t + ph + 18, max(pad_t + 14, ay))
            svg.append(f'<text x="{px:.2f}" y="{ay:.2f}" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="10.5" fill="{_esc(theme["ink_muted"])}">{_esc(lbl)}</text>')
        xv += x_step

    yv = math.ceil(y_min / y_step) * y_step
    while yv <= y_max + 1e-6:
        py = sy(yv)
        svg.append(f'<line x1="{pad_l}" y1="{py:.2f}" x2="{pad_l+pw}" y2="{py:.2f}" stroke="{_esc(theme["grid_line"])}" stroke-width="1"/>')
        if abs(yv) > 1e-6 or not (x_min <= 0 <= x_max):
            lbl = f"{yv:g}"
            ax = sx(0) - 8 if (x_min <= 0 <= x_max) else pad_l - 8
            ax = max(pad_l - 8, min(pad_l + pw - 8, ax))
            svg.append(f'<text x="{ax:.2f}" y="{py+4:.2f}" text-anchor="end" font-family="JetBrains Mono, monospace" font-size="10.5" fill="{_esc(theme["ink_muted"])}">{_esc(lbl)}</text>')
        yv += y_step

    # Cartesian axes with arrowheads
    if y_min <= 0 <= y_max:
        y0 = sy(0)
        svg.append(f'<line x1="{pad_l}" y1="{y0:.2f}" x2="{pad_l+pw+8}" y2="{y0:.2f}" stroke="{_esc(theme["ink_heading"])}" stroke-width="1.6"/>')
        svg.append(f'<polygon points="{pad_l+pw+12},{y0:.2f} {pad_l+pw+4},{y0-4:.2f} {pad_l+pw+4},{y0+4:.2f}" fill="{_esc(theme["ink_heading"])}"/>')
        svg.append(f'<text x="{pad_l+pw+14}" y="{y0+4:.2f}" font-size="12" font-style="italic" font-weight="700" fill="{_esc(theme["ink_heading"])}">{_esc(x_label)}</text>')
    if x_min <= 0 <= x_max:
        x0 = sx(0)
        svg.append(f'<line x1="{x0:.2f}" y1="{pad_t+ph}" x2="{x0:.2f}" y2="{pad_t-8}" stroke="{_esc(theme["ink_heading"])}" stroke-width="1.6"/>')
        svg.append(f'<polygon points="{x0:.2f},{pad_t-14} {x0-4:.2f},{pad_t-6} {x0+4:.2f},{pad_t-6}" fill="{_esc(theme["ink_heading"])}"/>')
        svg.append(f'<text x="{x0+8:.2f}" y="{pad_t-8}" font-size="12" font-style="italic" font-weight="700" fill="{_esc(theme["ink_heading"])}">{_esc(y_label)}</text>')

    # Optional shaded integral area (singularity-safe: splits cleanly across poles/discontinuities)
    if compiled_shade is not None:
        sh_obj, sh_tree, a_raw, b_raw = compiled_shade
        a_sh, b_sh = (a_raw, b_raw) if a_raw <= b_raw else (b_raw, a_raw)
        sh_col = str(sh_obj.get("color") or pal[0]["hex"])
        sh_segs = _sample_segments(sh_tree, a_sh, b_sh, 160, y_min, y_max, sx, sy)
        y_base = sy(0.0)
        for seg in sh_segs:
            pts_sh = [f"M {seg[0][2]:.2f},{y_base:.2f}"]
            for _, _, px_s, py_s in seg:
                pts_sh.append(f"L {px_s:.2f},{py_s:.2f}")
            pts_sh.append(f"L {seg[-1][2]:.2f},{y_base:.2f} Z")
            svg.append(
                f'<path class="math-shade" d="{" ".join(pts_sh)}" fill="{_esc(sh_col)}" '
                f'fill-opacity="0.14" clip-path="url(#math-plot-clip)"/>'
            )

    # Asymptotes (vertical, horizontal, and singularity-safe oblique)
    for asym, asym_tree in compiled_asymptotes:
        if "x" in asym:
            ax_v = sx(float(asym["x"]))
            svg.append(f'<line x1="{ax_v:.2f}" y1="{pad_t}" x2="{ax_v:.2f}" y2="{pad_t+ph}" stroke="{_esc(theme["ink_muted"])}" stroke-width="1.3" stroke-dasharray="6,4"/>')
        if "y" in asym:
            ay_v = sy(float(asym["y"]))
            svg.append(f'<line x1="{pad_l}" y1="{ay_v:.2f}" x2="{pad_l+pw}" y2="{ay_v:.2f}" stroke="{_esc(theme["ink_muted"])}" stroke-width="1.3" stroke-dasharray="6,4"/>')
        if asym_tree is not None:
            as_segs = _sample_segments(asym_tree, x_min, x_max, samples, y_min, y_max, sx, sy)
            for seg in as_segs:
                d_as = " ".join(f"{'M' if j == 0 else 'L'} {px_a:.2f},{py_a:.2f}" for j, (_, _, px_a, py_a) in enumerate(seg))
                svg.append(
                    f'<path d="{d_as}" fill="none" stroke="{_esc(theme["ink_muted"])}" '
                    f'stroke-width="1.3" stroke-dasharray="6,4" clip-path="url(#math-plot-clip)"/>'
                )

    # Plot function curves (splitting cleanly across discontinuities/poles)
    for idx, (fn, fn_tree) in enumerate(compiled_funcs):
        expr = fn["expr"]
        col = str(fn.get("color") or pal[idx % len(pal)]["hex"])
        dash = ' stroke-dasharray="6,4"' if fn.get("dashed") else ""
        segments = _sample_segments(fn_tree, x_min, x_max, samples, y_min, y_max, sx, sy)
        for seg in segments:
            d_str = " ".join(f"{'M' if j == 0 else 'L'} {px_c:.2f},{py_c:.2f}" for j, (_, _, px_c, py_c) in enumerate(seg))
            svg.append(
                f'<path class="math-curve" d="{d_str}" fill="none" stroke="{_esc(col)}" stroke-width="2.5"{dash} '
                f'clip-path="url(#math-plot-clip)" data-expr="{_esc(expr)}"/>'
            )

    # Highlighted points (extrema, roots, intersections)
    for pt in (spec.get("points") or []):
        px_v, py_v = float(pt["x"]), float(pt["y"])
        cx_p, cy_p = sx(px_v), sy(py_v)
        lbl = str(pt.get("label") or f"({px_v:g}, {py_v:g})")
        p_col = str(pt.get("color") or pal[0]["hex"])
        svg.append(f'<circle cx="{cx_p:.2f}" cy="{cy_p:.2f}" r="4.8" fill="{_esc(p_col)}" stroke="{_esc(theme["surface"])}" stroke-width="2"/>')
        dx_off = float(pt.get("dx", 8))
        dy_off = float(pt.get("dy", -10))
        svg.append(
            f'<text x="{cx_p+dx_off:.2f}" y="{cy_p+dy_off:.2f}" font-size="11.5" font-weight="600" fill="{_esc(theme["ink_heading"])}">'
            f'{_esc(lbl)}</text>'
        )

    svg.append("</svg>")
    return "\n".join(svg)


def main():
    ap = argparse.ArgumentParser(description="Plot mathematical functions y = f(x) to standalone SVG/HTML.")
    ap.add_argument("spec", help="JSON math plot specification")
    ap.add_argument("-o", "--output", required=True, help="Output .svg path")
    ap.add_argument("--html", default=None, help="Optional HTML wrapper output path")
    ap.add_argument("--theme", default="tech-warm-light", choices=["tech-warm-light", "tech-warm-dark"])
    args = ap.parse_args()

    try:
        with open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)

        theme = _load_theme(args.theme)
        svg_str = render_math_plot_svg(spec, theme_name=args.theme)
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + svg_str + "\n")
        sys.stderr.write(f"wrote {args.output}\n")

        if args.html:
            os.makedirs(os.path.dirname(os.path.abspath(args.html)), exist_ok=True)
            bg_canvas = _esc(theme["canvas"])
            fg_ink = _esc(theme["ink"])
            title_esc = _esc(spec.get("title") or "Math Plot")
            with open(args.html, "w", encoding="utf-8") as f:
                f.write(
                    f'<!DOCTYPE html><html lang="vi"><head><meta charset="utf-8">'
                    f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
                    f'<title>{title_esc}</title></head>'
                    f'<body style="margin:24px;background:{bg_canvas};color:{fg_ink};display:flex;justify-content:center">'
                    f'{svg_str}</body></html>\n'
                )
            sys.stderr.write(f"wrote {args.html}\n")
    except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
