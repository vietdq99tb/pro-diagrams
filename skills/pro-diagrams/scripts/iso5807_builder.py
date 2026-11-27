#!/usr/bin/env python3
"""Deterministic compiler from JSON diagram specs to uncompressed .drawio XML.

Supports:
  - kind: "iso5807-flowchart" (all 23 ISO 5807:1985 + standard symbols, auto layout & routing)
  - kind: "swimlane"          (cross-functional Pool + horizontal/vertical Swimlanes, no node/col cap)
  - kind: "topological-graph" (DAG, dependency network, tree, state graph)
  - kind: "cpm"               (Critical Path Method network with auto ES/EF/LS/LF/TF & Terracotta critical path)

Applies the 'Atelier Technical Warm' ('tech-warm-light' / 'tech-warm-dark') design system,
Open Sans Vietnamese typography sizing, 10px grid snapping, and collision-free orthogonal waypoints.

Usage:
  python3 iso5807_builder.py spec.json -o diagram.drawio [--preset tech-warm-light] [--render-svg diagram.svg]
"""
import argparse
import html
import json
import math
import os
import sys
import textwrap
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)


def _snap(v, grid=10):
    return int(round(float(v) / grid) * grid)


def _load_json(rel_path):
    with open(os.path.join(SKILL_DIR, rel_path), encoding="utf-8") as f:
        return json.load(f)


def _wrap_lines(label, max_chars=22):
    raw_lines = str(label or "").replace("<br>", "\n").replace("<br/>", "\n").split("\n")
    out = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        wrapped = textwrap.wrap(line, width=max_chars, break_long_words=False, break_on_hyphens=False)
        out.extend(wrapped or [line])
    return out or [""]


def _measure_node_box(sym_key, label, sym_catalog):
    info = sym_catalog.get(sym_key) or sym_catalog["process"]
    dw, dh = info["default_width"], info["default_height"]
    if sym_key == "terminator":
        dh = max(dh, 60)
    if sym_key in ("on_page_connector", "parallel_mode"):
        return _snap(dw), _snap(dh)
    if sym_key == "off_page_connector":
        return _snap(max(dw, 70)), _snap(max(dh, 60))

    max_chars = 18 if sym_key == "decision" else 24
    lines = _wrap_lines(label, max_chars=max_chars)
    longest = max((len(l) for l in lines), default=1)
    n_lines = len(lines)

    # Open Sans 12px Vietnamese width & stacked-diacritic height allowance
    px_per_char = 7.4
    pad_x = 46 if sym_key == "decision" else (34 if sym_key in ("data", "preparation", "predefined_process", "manual_operation") else 24)
    pad_y = 38 if sym_key == "decision" else (28 if sym_key == "database" else 22)
    line_h = 19

    calc_w = longest * px_per_char + pad_x
    calc_h = n_lines * line_h + pad_y
    if sym_key == "decision":
        # Rhombus inscribes a half-area rectangle; keep generous aspect ratio
        calc_w = max(calc_w * 1.22, dw)
        calc_h = max(calc_h * 1.18, dh)
    w = _snap(max(dw, min(calc_w, 260)))
    h = _snap(max(dh, min(calc_h, 150)))
    return w, h


def _compute_dag_ranks_and_backedges(node_ids, edges, explicit_ranks=None):
    """Break cycles via DFS, then assign longest-path topological ranks."""
    explicit_ranks = explicit_ranks or {}
    adj = defaultdict(list)
    indeg_raw = defaultdict(int)
    for src, tgt, eid in edges:
        if src in node_ids and tgt in node_ids:
            adj[src].append((tgt, eid))
            indeg_raw[tgt] += 1

    # Start DFS from in-degree 0 nodes first, preserving spec order
    roots = [n for n in node_ids if indeg_raw[n] == 0]
    order_seeds = roots + [n for n in node_ids if n not in roots]

    state = {}  # 0=unvisited, 1=visiting, 2=done
    back_edge_ids = set()

    def dfs(u):
        state[u] = 1
        for v, eid in adj[u]:
            st = state.get(v, 0)
            if st == 1:
                back_edge_ids.add(eid)
            elif st == 0:
                dfs(v)
        state[u] = 2

    for seed in order_seeds:
        if state.get(seed, 0) == 0:
            dfs(seed)

    # Build DAG without back-edges
    dag_adj = defaultdict(list)
    dag_indeg = {n: 0 for n in node_ids}
    for src, tgt, eid in edges:
        if eid in back_edge_ids or src not in node_ids or tgt not in node_ids or src == tgt:
            continue
        dag_adj[src].append(tgt)
        dag_indeg[tgt] += 1

    ranks = {n: int(explicit_ranks[n]) if n in explicit_ranks else 0 for n in node_ids}
    q = deque([n for n in node_ids if dag_indeg[n] == 0])
    visited = set()
    while q:
        u = q.popleft()
        visited.add(u)
        for v in dag_adj[u]:
            if v not in explicit_ranks:
                ranks[v] = max(ranks[v], ranks[u] + 1)
            dag_indeg[v] -= 1
            if dag_indeg[v] == 0:
                q.append(v)

    # Fallback for any leftover cycle components
    for n in node_ids:
        if n not in visited and n not in explicit_ranks:
            ranks[n] = max(ranks.values(), default=0) + 1
    return ranks, back_edge_ids


def _compute_cpm(nodes, edges, back_edge_ids):
    """Compute ES, EF, LS, LF, TF and return (metrics_by_id, critical_nodes, critical_edge_ids)."""
    node_ids = [n["id"] for n in nodes]
    dur = {n["id"]: float(n.get("duration", 0)) for n in nodes}
    adj = defaultdict(list)
    rev = defaultdict(list)
    indeg = {nid: 0 for nid in node_ids}
    for e in edges:
        eid, u, v = e["id"], e["from"], e["to"]
        if eid in back_edge_ids or u not in dur or v not in dur:
            continue
        adj[u].append((v, eid))
        rev[v].append((u, eid))
        indeg[v] += 1

    topo = []
    q = deque([nid for nid in node_ids if indeg[nid] == 0])
    while q:
        u = q.popleft()
        topo.append(u)
        for v, _ in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)

    es, ef = {}, {}
    for u in topo:
        es[u] = max((ef[p] for p, _ in rev[u]), default=0.0)
        ef[u] = es[u] + dur[u]

    project_end = max(ef.values(), default=0.0)
    ls, lf = {}, {}
    for u in reversed(topo):
        lf[u] = min((ls[s] for s, _ in adj[u]), default=project_end)
        ls[u] = lf[u] - dur[u]

    metrics = {}
    crit_nodes = set()
    for nid in node_ids:
        if nid not in es:
            continue
        tf = round(ls[nid] - es[nid], 4)
        is_crit = abs(tf) < 1e-6
        if is_crit:
            crit_nodes.add(nid)
        metrics[nid] = {
            "duration": dur[nid],
            "ES": es[nid],
            "EF": ef[nid],
            "LS": ls[nid],
            "LF": lf[nid],
            "TF": 0.0 if is_crit else tf,
            "critical": is_crit,
        }

    crit_edges = set()
    for e in edges:
        eid, u, v = e["id"], e["from"], e["to"]
        if u in crit_nodes and v in crit_nodes and abs(ef[u] - es[v]) < 1e-6:
            crit_edges.add(eid)
    return metrics, crit_nodes, crit_edges, project_end


def _fmt_num(x):
    return str(int(x)) if abs(x - round(x)) < 1e-6 else f"{x:.1f}"


def _is_affirmative_label(lbl):
    s = (lbl or "").strip().lower()
    if not s:
        return True
    neg_prefixes = ("không", "no", "false", "sai", "lỗi", "fail", "từ chối", "reject", "hủy", "quá hạn", "thiếu", "vượt")
    if any(s.startswith(p) or p in s for p in neg_prefixes):
        return False
    return True


def _safe_style_val(val):
    return str(val or "").replace(";", "").replace("\r", "").replace("\n", "").strip()


def _hex_luminance(hex_color):
    s = str(hex_color or "").strip()
    if len(s) != 7 or not s.startswith("#"):
        return 0.9
    try:
        rgb = [int(s[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    except ValueError:
        return 0.9
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _resolve_preset(preset_key):
    """Resolve a built-in preset name, user style name, or direct JSON file path."""
    builtin_dir = os.path.join(SKILL_DIR, "styles", "built-in")
    known = sorted(f[:-5] for f in os.listdir(builtin_dir) if f.endswith(".json"))
    key = str(preset_key or "tech-warm-light").strip()
    candidates = []
    if os.path.isfile(key):
        candidates.append(key)
    else:
        candidates.append(os.path.join(builtin_dir, f"{key}.json"))
        candidates.append(os.path.expanduser(f"~/.pro-diagrams/styles/{key}.json"))
    for path in candidates:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "palette" not in data or "font" not in data:
                raise ValueError(f"invalid style preset JSON: {path}")
            return data
    raise ValueError(f"preset {key!r} not found (built-ins: {', '.join(known)})")


def _orient(a, b, c):
    v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)


def _segments_cross(p1, p2, p3, p4):
    o1, o2 = _orient(p1, p2, p3), _orient(p1, p2, p4)
    o3, o4 = _orient(p3, p4, p1), _orient(p3, p4, p2)
    return o1 != o2 and o3 != o4 and 0 not in (o1, o2, o3, o4)


def _point_in_rect(p, box, eps=1e-6):
    x, y, w, h = box
    return x + eps < p[0] < x + w - eps and y + eps < p[1] < y + h - eps


def _route_hits_rect_exact(points, box):
    x, y, w, h = box
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    borders = list(zip(corners, corners[1:] + corners[:1]))
    for a, b in zip(points, points[1:]):
        if _point_in_rect(a, box) or _point_in_rect(b, box):
            return True
        if any(_segments_cross(a, b, c, d) for c, d in borders):
            return True
    return False


def _routes_cross(pa, pb):
    for a1, a2 in zip(pa, pa[1:]):
        for b1, b2 in zip(pb, pb[1:]):
            if _segments_cross(a1, a2, b1, b2):
                return True
    return False


def _boxes_overlap(a, b, pad=4):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax - pad < bx + bw and bx - pad < ax + aw
            and ay - pad < by + bh and by - pad < ay + ah)


def _boxes_intersect_seg(x1, y1, x2, y2, box, pad=6):
    bx, by, bw, bh = box
    lx, rx = bx - pad, bx + bw + pad
    ty, by2 = by - pad, by + bh + pad
    if abs(x1 - x2) < 1e-3:  # vertical
        x = x1
        ylo, yhi = min(y1, y2), max(y1, y2)
        return lx < x < rx and yhi > ty and ylo < by2
    if abs(y1 - y2) < 1e-3:  # horizontal
        y = y1
        xlo, xhi = min(x1, x2), max(x1, x2)
        return ty < y < by2 and xhi > lx and xlo < rx
    return _route_hits_rect_exact([(x1, y1), (x2, y2)], (lx, ty, rx - lx, by2 - ty))


def _route_hits_any_box(pts, obstacle_boxes, pad=4):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        for b in obstacle_boxes:
            if _boxes_intersect_seg(x1, y1, x2, y2, b, pad=pad):
                return True
    return False


def _count_route_box_hits(pts, obstacle_boxes, pad=0):
    hits = 0
    for b in obstacle_boxes:
        if pad == 0:
            if _route_hits_rect_exact(pts, b):
                hits += 1
        else:
            if any(_boxes_intersect_seg(a[0], a[1], c[0], c[1], b, pad=pad)
                   for a, c in zip(pts, pts[1:])):
                hits += 1
    return hits


def _count_border_hits(pts, lane_borders_x, lane_borders_y):
    hits = 0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if abs(x1 - x2) < 1.0 and abs(y2 - y1) > 40:
            if any(abs(x1 - bx) < 5.0 for bx in lane_borders_x):
                hits += 1
        if abs(y1 - y2) < 1.0 and abs(x2 - x1) > 40:
            if any(abs(y1 - by) < 5.0 for by in lane_borders_y):
                hits += 1
    return hits


def _avoid_border(coord, borders, step=20):
    c = _snap(coord)
    if not borders:
        return c
    if not any(abs(c - b) < 10 for b in borders):
        return c
    for delta in (step, -step, 2 * step, -2 * step):
        cand = _snap(c + delta)
        if not any(abs(cand - b) < 10 for b in borders):
            return cand
    return c


def _valid_port_directions(pts, ex_x, ex_y, en_x, en_y):
    """Ensure first segment exits outward from source port and last enters from outside."""
    if len(pts) < 2:
        return True
    p0, p1 = pts[0], pts[1]
    pn_1, pn = pts[-2], pts[-1]
    eps = 1.0
    if ex_x == 1.0 and p1[0] < p0[0] - eps:
        return False
    if ex_x == 0.0 and p1[0] > p0[0] + eps:
        return False
    if ex_y == 1.0 and p1[1] < p0[1] - eps:
        return False
    if ex_y == 0.0 and p1[1] > p0[1] + eps:
        return False
    if en_x == 1.0 and pn_1[0] < pn[0] - eps:
        return False
    if en_x == 0.0 and pn_1[0] > pn[0] + eps:
        return False
    if en_y == 1.0 and pn_1[1] < pn[1] - eps:
        return False
    if en_y == 0.0 and pn_1[1] > pn[1] + eps:
        return False
    return True


def _manhattan_len(pts):
    return sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def _dedupe_waypoints(waypoints):
    clean = []
    for p in waypoints:
        p_int = (int(round(p[0])), int(round(p[1])))
        if not clean or clean[-1] != p_int:
            clean.append(p_int)
    return clean


def compile_spec_to_drawio(spec, preset_name=None):
    """Compile a dict spec into an uncompressed .drawio XML ElementTree."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object")
    raw_nodes_in = spec.get("nodes")
    if not isinstance(raw_nodes_in, list) or not raw_nodes_in:
        raise ValueError("spec must contain a non-empty 'nodes' list")

    sym_catalog = _load_json("data/iso5807-shapes.json")["symbols"]
    preset_key = preset_name or spec.get("preset") or "tech-warm-light"
    preset = _resolve_preset(preset_key)

    tokens_all = _load_json("data/theme-tokens.json")["themes"]
    preset_extras = preset.get("extras") or {}
    if preset.get("name") in tokens_all:
        theme_tok = dict(tokens_all[preset["name"]])
    else:
        bg_guess = preset_extras.get("background", "#F8F6F2")
        base_name = "tech-warm-dark" if _hex_luminance(bg_guess) < 0.25 else "tech-warm-light"
        theme_tok = dict(tokens_all[base_name])
        if preset_extras.get("background"):
            theme_tok["edge_label_bg"] = preset_extras["background"]
        accent_stroke = (preset.get("palette") or {}).get("accent", {}).get("strokeColor")
        if accent_stroke:
            theme_tok["edge_critical"] = accent_stroke

    palette = preset["palette"]
    font_family = _safe_style_val(preset["font"]["fontFamily"])
    font_size = preset["font"]["fontSize"]
    font_color = _safe_style_val(preset_extras.get("fontColor", theme_tok["ink"]))
    stroke_w = preset_extras.get("globalStrokeWidth", 1.5)

    kind = (spec.get("kind") or "iso5807-flowchart").lower()
    direction = (spec.get("direction") or ("LR" if kind in ("cpm", "topological-graph") else "TB")).upper()
    title = spec.get("title") or "Sơ đồ Quy trình Chuẩn ISO 5807"
    subtitle = spec.get("subtitle") or ""
    unit = spec.get("duration_unit") or "ngày"

    lanes_spec = list(spec.get("lanes") or [])
    has_swimlanes = (kind == "swimlane") or bool(lanes_spec)

    # Reserve all structural, lane, and node IDs BEFORE assigning edge IDs (prevents E-DUP-ID)
    used_ids = {"0", "1", "title_banner"}
    if has_swimlanes and lanes_spec:
        if spec.get("pool_title"):
            used_ids.add("pool_main")
        for lspec in lanes_spec:
            lid = str(lspec.get("id") or "").strip()
            if not lid:
                raise ValueError("each swimlane must define a non-empty 'id'")
            if lid in used_ids:
                raise ValueError(f"duplicate or reserved lane id {lid!r}")
            used_ids.add(lid)

    # Separate annotation nodes from flow nodes with strict duplicate ID checking
    flow_nodes = []
    annot_nodes = []
    alias_map = {
        "start": "terminator", "end": "terminator",
        "io": "data", "input": "data", "output": "data",
        "subroutine": "predefined_process", "subprocess": "predefined_process",
        "connector": "on_page_connector", "offpage": "off_page_connector",
        "db": "database", "manual": "manual_operation",
        "comment": "annotation", "note": "annotation",
    }
    auto_node_seq = 1
    for n in raw_nodes_in:
        if not isinstance(n, dict):
            raise ValueError("each entry in 'nodes' must be a JSON object")
        ncopy = dict(n)
        if n.get("id") is not None and str(n.get("id")).strip() != "":
            nid = str(n["id"])
            if nid in used_ids:
                raise ValueError(f"duplicate or reserved node id {nid!r}")
        else:
            while f"n{auto_node_seq}" in used_ids:
                auto_node_seq += 1
            nid = f"n{auto_node_seq}"
            auto_node_seq += 1
        used_ids.add(nid)
        ncopy["id"] = nid

        ntype = str(n.get("type") or "process").lower()
        ncopy["type"] = alias_map.get(ntype, ntype)
        if ncopy["type"] == "annotation":
            annot_nodes.append(ncopy)
        else:
            flow_nodes.append(ncopy)

    # Assign collision-free edge IDs (and reject explicit duplicate IDs)
    raw_edges = []
    auto_edge_fallback = 1
    for idx, e in enumerate(spec.get("edges") or []):
        if not isinstance(e, dict):
            raise ValueError("each entry in 'edges' must be a JSON object")
        if e.get("id") is not None and str(e.get("id")).strip() != "":
            eid = str(e["id"])
            if eid in used_ids:
                raise ValueError(f"duplicate or reserved edge id {eid!r}")
        else:
            cand = f"e{idx + 1}"
            if cand not in used_ids:
                eid = cand
            else:
                while f"edge_{auto_edge_fallback}" in used_ids:
                    auto_edge_fallback += 1
                eid = f"edge_{auto_edge_fallback}"
                auto_edge_fallback += 1
        used_ids.add(eid)
        src = e.get("from") if "from" in e else e.get("source")
        tgt = e.get("to") if "to" in e else e.get("target")
        raw_edges.append({
            "id": eid,
            "from": str(src) if src is not None else "",
            "to": str(tgt) if tgt is not None else "",
            "label": str(e.get("label") or ""),
            "style_role": str(e.get("role") or ""),
            "dashed": bool(e.get("dashed", False)),
        })

    flow_ids = [n["id"] for n in flow_nodes]
    explicit_ranks = {n["id"]: n["rank"] for n in flow_nodes if "rank" in n}
    edge_tuples = [(e["from"], e["to"], e["id"]) for e in raw_edges]
    ranks, back_edge_ids = _compute_dag_ranks_and_backedges(flow_ids, edge_tuples, explicit_ranks)

    # Outgoing on_page_connector (in-degree=0, out-degree>=1) sits right before its target rank
    in_deg_map = defaultdict(int)
    out_targets = defaultdict(list)
    for e in raw_edges:
        if e["from"] in ranks and e["to"] in ranks and e["id"] not in back_edge_ids:
            in_deg_map[e["to"]] += 1
            out_targets[e["from"]].append(e["to"])
    for n in flow_nodes:
        nid = n["id"]
        if n["type"] == "on_page_connector" and nid not in explicit_ranks:
            if in_deg_map[nid] == 0 and out_targets[nid]:
                tgt_min_rank = min(ranks[t] for t in out_targets[nid])
                ranks[nid] = max(0, tgt_min_rank - 1)

    # Optional CPM computation
    cpm_metrics, crit_nodes, crit_edges, project_end = {}, set(), set(), 0.0
    if kind == "cpm" or any("duration" in n for n in flow_nodes):
        cpm_metrics, crit_nodes, crit_edges, project_end = _compute_cpm(flow_nodes, raw_edges, back_edge_ids)
        if kind == "cpm" and not subtitle:
            crit_hex = _safe_style_val(theme_tok["edge_critical"])
            subtitle = (
                f"Tổng thời gian đường găng (Critical Path): {_fmt_num(project_end)} {unit} · "
                f"Màu Gốm nung ({crit_hex}) biểu thị nút găng (TF = 0)"
            )

    # Format labels & measure boxes
    boxes_wh = {}
    formatted_labels = {}
    for n in flow_nodes:
        nid = n["id"]
        lbl = str(n.get("label") or nid)
        if nid in cpm_metrics:
            m = cpm_metrics[nid]
            code_tag = str(n.get("code") or nid.upper())
            dur_s = _fmt_num(m["duration"])
            es_s, ef_s = _fmt_num(m["ES"]), _fmt_num(m["EF"])
            ls_s, lf_s = _fmt_num(m["LS"]), _fmt_num(m["LF"])
            tf_s = _fmt_num(m["TF"])
            lbl_plain = (
                f"{code_tag}: {lbl}\n"
                f"⏱ {dur_s} {unit} · TF={tf_s}\n"
                f"ES={es_s}→EF={ef_s} · LS={ls_s}→LF={lf_s}"
            )
            lbl_html = (
                f"<b>{html.escape(code_tag)}: {html.escape(lbl)}</b><br/>"
                f"<font style='font-size:10px'>⏱ {dur_s} {html.escape(unit)} · TF={tf_s}</font><br/>"
                f"<font style='font-size:10px'>ES={es_s}→EF={ef_s} · LS={ls_s}→LF={lf_s}</font>"
            )
            w, h = _measure_node_box(n["type"], lbl_plain, sym_catalog)
            w = _snap(max(w, 210))
            h = _snap(max(h, 86))
            boxes_wh[nid] = (w, h)
            formatted_labels[nid] = lbl_html
        else:
            w, h = _measure_node_box(n["type"], lbl, sym_catalog)
            boxes_wh[nid] = (w, h)
            formatted_labels[nid] = html.escape(lbl).replace("\n", "<br/>")

    for an in annot_nodes:
        aid = an["id"]
        lbl = str(an.get("label") or "")
        w, h = _measure_node_box("annotation", lbl, sym_catalog)
        boxes_wh[aid] = (w, h)
        formatted_labels[aid] = html.escape(lbl).replace("\n", "<br/>")

    # Header block height & outer margins (leave breathing room for left loop corridors if needed)
    header_h = 80 if subtitle else 60
    margin_x = 120 if back_edge_ids else 90
    margin_y = 30 + header_h

    abs_boxes = {}       # nid -> (x, y, w, h) in page coords
    parent_map = {}      # nid -> mxCell parent id
    rel_boxes = {}       # nid -> (rx, ry, w, h) inside parent
    lane_cells = []      # list of (lid, ltitle, lx, ly, lw, lh, parent_id, style)
    lane_abs_rects = []  # absolute (x, y, w, h) of all swimlane containers

    max_rank = max(ranks.values(), default=0)
    by_node = {n["id"]: n for n in flow_nodes}

    if has_swimlanes and lanes_spec:
        lane_ids = [str(l["id"]) for l in lanes_spec]
        grid_cells = defaultdict(list)
        for n in flow_nodes:
            lid = str(n.get("lane") or lane_ids[0])
            if lid not in lane_ids:
                lid = lane_ids[0]
            grid_cells[(lid, ranks[n["id"]])].append(n["id"])

        sw_tok = theme_tok["swimlane"]
        pool_hdr_fill = _safe_style_val(sw_tok["pool_header_fill"])
        pool_hdr_txt = _safe_style_val(sw_tok["pool_header_text"])
        lane_hdr_fill = _safe_style_val(sw_tok["lane_header_fill"])
        lane_hdr_txt = _safe_style_val(sw_tok["lane_header_text"])
        lane_hdr_strk = _safe_style_val(sw_tok["lane_header_stroke"])
        surf_bg = _safe_style_val(theme_tok["surface"])

        if direction == "TB":
            lane_widths = {}
            for lid in lane_ids:
                max_stack_w = 240
                for r in range(max_rank + 1):
                    nids_here = grid_cells.get((lid, r), [])
                    if nids_here:
                        sw = sum(boxes_wh[nid][0] for nid in nids_here) + 40 * (len(nids_here) - 1) + 80
                        max_stack_w = max(max_stack_w, sw)
                lane_widths[lid] = _snap(max_stack_w)

            rank_heights = {}
            for r in range(max_rank + 1):
                mh = 70
                for lid in lane_ids:
                    for nid in grid_cells.get((lid, r), []):
                        mh = max(mh, boxes_wh[nid][1])
                rank_heights[r] = _snap(mh)

            rank_gap_y = 80
            lane_hdr_h = 40
            pool_hdr_h = 38 if spec.get("pool_title") else 0
            cur_y = pool_hdr_h + lane_hdr_h + 40
            rank_y = {}
            for r in range(max_rank + 1):
                rank_y[r] = _snap(cur_y)
                cur_y += rank_heights[r] + rank_gap_y
            total_lane_h = _snap(cur_y - pool_hdr_h + 30)
            total_pool_w = sum(lane_widths.values())
            pool_x, pool_y = _snap(margin_x), _snap(margin_y)

            pool_id = "pool_main" if spec.get("pool_title") else "1"
            if spec.get("pool_title"):
                pool_style = (
                    f"swimlane;whiteSpace=wrap;html=1;startSize={pool_hdr_h};horizontal=1;"
                    f"fillColor={pool_hdr_fill};fontColor={pool_hdr_txt};"
                    f"strokeColor={pool_hdr_fill};fontFamily={font_family};fontSize=14;fontStyle=1;"
                    f"swimlaneFillColor={surf_bg};"
                )
                lane_cells.append((
                    pool_id, html.escape(str(spec["pool_title"])),
                    pool_x, pool_y, total_pool_w, pool_hdr_h + total_lane_h, "1", pool_style
                ))
                lane_abs_rects.append((pool_x, pool_y, total_pool_w, pool_hdr_h + total_lane_h))

            lx_cursor = 0 if pool_id != "1" else pool_x
            ly_fixed = pool_hdr_h if pool_id != "1" else pool_y
            for idx, lspec in enumerate(lanes_spec):
                lid = str(lspec["id"])
                lw = lane_widths[lid]
                body_bg = _safe_style_val(sw_tok["lane_body_even"] if idx % 2 == 0 else sw_tok["lane_body_odd"])
                lstyle = (
                    f"swimlane;whiteSpace=wrap;html=1;startSize={lane_hdr_h};horizontal=1;"
                    f"fillColor={lane_hdr_fill};fontColor={lane_hdr_txt};"
                    f"strokeColor={lane_hdr_strk};swimlaneFillColor={body_bg};"
                    f"fontFamily={font_family};fontSize=13;fontStyle=1;"
                )
                lane_cells.append((
                    lid, html.escape(str(lspec.get("title") or lid)),
                    lx_cursor, ly_fixed, lw, total_lane_h, pool_id, lstyle
                ))
                abs_lx = (pool_x + lx_cursor) if pool_id != "1" else lx_cursor
                abs_ly = (pool_y + ly_fixed) if pool_id != "1" else ly_fixed
                lane_abs_rects.append((abs_lx, abs_ly, lw, total_lane_h))

                for r in range(max_rank + 1):
                    nids_here = grid_cells.get((lid, r), [])
                    if not nids_here:
                        continue
                    tot_w = sum(boxes_wh[nid][0] for nid in nids_here) + 40 * (len(nids_here) - 1)
                    start_rx = _snap((lw - tot_w) / 2)
                    ry_base = rank_y[r] - pool_hdr_h
                    rx = start_rx
                    for nid in nids_here:
                        w, h = boxes_wh[nid]
                        ry = _snap(ry_base + (rank_heights[r] - h) / 2)
                        rel_boxes[nid] = (rx, ry, w, h)
                        abs_boxes[nid] = (abs_lx + rx, abs_ly + ry, w, h)
                        parent_map[nid] = lid
                        rx += w + 40
                lx_cursor += lw
        else:
            rank_widths = {}
            for r in range(max_rank + 1):
                mw = 160
                for lid in lane_ids:
                    for nid in grid_cells.get((lid, r), []):
                        mw = max(mw, boxes_wh[nid][0])
                rank_widths[r] = _snap(mw)

            lane_heights = {}
            for lid in lane_ids:
                max_stack_h = 150
                for r in range(max_rank + 1):
                    nids_here = grid_cells.get((lid, r), [])
                    if nids_here:
                        sh = sum(boxes_wh[nid][1] for nid in nids_here) + 30 * (len(nids_here) - 1) + 70
                        max_stack_h = max(max_stack_h, sh)
                lane_heights[lid] = _snap(max_stack_h)

            rank_gap_x = 90
            lane_hdr_w = 44
            pool_hdr_w = 40 if spec.get("pool_title") else 0
            cur_x = lane_hdr_w + 50
            rank_x = {}
            for r in range(max_rank + 1):
                rank_x[r] = _snap(cur_x)
                cur_x += rank_widths[r] + rank_gap_x
            total_lane_w = _snap(cur_x + 40)
            total_pool_h = sum(lane_heights.values())
            pool_x, pool_y = _snap(margin_x), _snap(margin_y)

            pool_id = "pool_main" if spec.get("pool_title") else "1"
            if spec.get("pool_title"):
                pool_style = (
                    f"swimlane;whiteSpace=wrap;html=1;startSize={pool_hdr_w};horizontal=0;"
                    f"fillColor={pool_hdr_fill};fontColor={pool_hdr_txt};"
                    f"strokeColor={pool_hdr_fill};fontFamily={font_family};fontSize=14;fontStyle=1;"
                    f"swimlaneFillColor={surf_bg};"
                )
                lane_cells.append((
                    pool_id, html.escape(str(spec["pool_title"])),
                    pool_x, pool_y, pool_hdr_w + total_lane_w, total_pool_h, "1", pool_style
                ))
                lane_abs_rects.append((pool_x, pool_y, pool_hdr_w + total_lane_w, total_pool_h))

            ly_cursor = 0 if pool_id != "1" else pool_y
            lx_fixed = pool_hdr_w if pool_id != "1" else pool_x
            for idx, lspec in enumerate(lanes_spec):
                lid = str(lspec["id"])
                lh = lane_heights[lid]
                body_bg = _safe_style_val(sw_tok["lane_body_even"] if idx % 2 == 0 else sw_tok["lane_body_odd"])
                lstyle = (
                    f"swimlane;whiteSpace=wrap;html=1;startSize={lane_hdr_w};horizontal=0;"
                    f"fillColor={lane_hdr_fill};fontColor={lane_hdr_txt};"
                    f"strokeColor={lane_hdr_strk};swimlaneFillColor={body_bg};"
                    f"fontFamily={font_family};fontSize=13;fontStyle=1;"
                )
                lane_cells.append((
                    lid, html.escape(str(lspec.get("title") or lid)),
                    lx_fixed, ly_cursor, total_lane_w, lh, pool_id, lstyle
                ))
                abs_lx = (pool_x + lx_fixed) if pool_id != "1" else lx_fixed
                abs_ly = (pool_y + ly_cursor) if pool_id != "1" else ly_cursor
                lane_abs_rects.append((abs_lx, abs_ly, total_lane_w, lh))

                for r in range(max_rank + 1):
                    nids_here = grid_cells.get((lid, r), [])
                    if not nids_here:
                        continue
                    tot_h = sum(boxes_wh[nid][1] for nid in nids_here) + 30 * (len(nids_here) - 1)
                    start_ry = _snap((lh - tot_h) / 2)
                    rx_base = rank_x[r]
                    ry = start_ry
                    for nid in nids_here:
                        w, h = boxes_wh[nid]
                        rx = _snap(rx_base + (rank_widths[r] - w) / 2)
                        rel_boxes[nid] = (rx, ry, w, h)
                        abs_boxes[nid] = (abs_lx + rx, abs_ly + ry, w, h)
                        parent_map[nid] = lid
                        ry += h + 30
                ly_cursor += lh
    else:
        # Free layered layout (barycenter ordering + adjacent crossing swap + explicit `col` support)
        layers = defaultdict(list)
        for nid in flow_ids:
            layers[ranks[nid]].append(nid)

        preds = defaultdict(list)
        succs = defaultdict(list)
        for e in raw_edges:
            if e["id"] not in back_edge_ids and e["from"] in ranks and e["to"] in ranks:
                preds[e["to"]].append((e["from"], e["label"]))
                succs[e["from"]].append((e["to"], e["label"]))

        def _pair_crossings(order, neighbor_map, ref_pos):
            idx_map = {n: i for i, n in enumerate(order)}
            edge_pairs = []
            for n in order:
                for nb, _ in neighbor_map.get(n, []):
                    if nb in ref_pos:
                        edge_pairs.append((ref_pos[nb], idx_map[n]))
            cnt = 0
            for i in range(len(edge_pairs)):
                for j in range(i + 1, len(edge_pairs)):
                    a1, b1 = edge_pairs[i]
                    a2, b2 = edge_pairs[j]
                    if (a1 < a2 and b1 > b2) or (a1 > a2 and b1 < b2):
                        cnt += 1
            return cnt

        def _swap_minimize(order, neighbor_map, ref_pos):
            if len(order) <= 1 or any("col" in by_node[n] for n in order):
                return
            improved = True
            while improved:
                improved = False
                cur_c = _pair_crossings(order, neighbor_map, ref_pos)
                for i in range(len(order) - 1):
                    order[i], order[i + 1] = order[i + 1], order[i]
                    new_c = _pair_crossings(order, neighbor_map, ref_pos)
                    if new_c < cur_c:
                        cur_c = new_c
                        improved = True
                    else:
                        order[i], order[i + 1] = order[i + 1], order[i]

        def _refresh_pos(r_idx):
            nids = layers[r_idx]
            mid = (len(nids) - 1) / 2.0
            for i, nid in enumerate(nids):
                pos_index[nid] = float(by_node[nid].get("col", i - mid))

        pos_index = {}
        # Pass 1: Top-down barycenter + adjacent swap
        for r in range(max_rank + 1):
            nids = layers[r]
            if r == 0:
                nids.sort(key=lambda nid: float(by_node[nid].get("col", 0)))
            else:
                def sort_key_td(nid):
                    if "col" in by_node[nid]:
                        return float(by_node[nid]["col"])
                    ps = preds.get(nid, [])
                    if not ps:
                        if by_node[nid]["type"] == "on_page_connector":
                            # Align near co-predecessors of its target if already placed
                            co_vals = []
                            for t, _ in succs.get(nid, []):
                                for cp, _ in preds.get(t, []):
                                    if cp != nid and cp in pos_index:
                                        co_vals.append(pos_index[cp] + 0.15)
                            return sum(co_vals) / len(co_vals) if co_vals else 0.85
                        return 0.0
                    vals = []
                    for p, elbl in ps:
                        base = pos_index.get(p, 0.0)
                        if by_node[p]["type"] == "decision" and not _is_affirmative_label(elbl):
                            base += 0.65
                        vals.append(base)
                    return sum(vals) / len(vals)
                nids.sort(key=sort_key_td)
                _swap_minimize(nids, preds, pos_index)
            layers[r] = nids
            _refresh_pos(r)

        # Pass 2: Bottom-up barycenter + adjacent swap (aligns multi-predecessor & zero-indegree nodes)
        for r in range(max_rank - 1, -1, -1):
            nids = layers[r]
            if len(nids) > 1 and not any("col" in by_node[n] for n in nids):
                def sort_key_bu(nid):
                    ss = succs.get(nid, [])
                    ps = preds.get(nid, [])
                    vals = []
                    for s, _ in ss:
                        if s in pos_index:
                            vals.append(pos_index[s])
                    for p, elbl in ps:
                        if p in pos_index:
                            base = pos_index[p]
                            if by_node[p]["type"] == "decision" and not _is_affirmative_label(elbl):
                                base += 0.65
                            vals.append(base)
                    return (sum(vals) / len(vals)) if vals else pos_index.get(nid, 0.0)
                nids.sort(key=sort_key_bu)
                _swap_minimize(nids, succs, pos_index)
                layers[r] = nids
                _refresh_pos(r)

        # Pass 3: Top-down refinement
        for r in range(1, max_rank + 1):
            nids = layers[r]
            if len(nids) > 1 and not any("col" in by_node[n] for n in nids):
                def sort_key_ref(nid):
                    ps = preds.get(nid, [])
                    if not ps:
                        return pos_index.get(nid, 0.0)
                    vals = []
                    for p, elbl in ps:
                        base = pos_index.get(p, 0.0)
                        if by_node[p]["type"] == "decision" and not _is_affirmative_label(elbl):
                            base += 0.65
                        vals.append(base)
                    return sum(vals) / len(vals)
                nids.sort(key=sort_key_ref)
                _swap_minimize(nids, preds, pos_index)
                layers[r] = nids
                _refresh_pos(r)

        if direction == "TB":
            col_gap = 90
            row_gap = 80
            layer_widths = {}
            layer_heights = {}
            for r in range(max_rank + 1):
                nids = layers[r]
                if not nids:
                    layer_widths[r] = 0
                    layer_heights[r] = 60
                    continue
                layer_widths[r] = sum(boxes_wh[n][0] for n in nids) + col_gap * (len(nids) - 1)
                layer_heights[r] = max(boxes_wh[n][1] for n in nids)
            spine_cx = _snap(margin_x + max(layer_widths.values(), default=260) / 2 + 60)

            cur_y = margin_y + 20
            for r in range(max_rank + 1):
                nids = layers[r]
                if not nids:
                    cur_y += 60
                    continue
                if any("col" in by_node[n] for n in nids):
                    col_step = 260
                    placed_row = []
                    for nid in nids:
                        w, h = boxes_wh[nid]
                        cval = float(by_node[nid].get("col", pos_index[nid]))
                        x = _snap(spine_cx + cval * col_step - w / 2)
                        y = _snap(cur_y + (layer_heights[r] - h) / 2)
                        placed_row.append([nid, x, y, w, h])
                    placed_row.sort(key=lambda item: item[1])
                    for i in range(1, len(placed_row)):
                        prev_right = placed_row[i - 1][1] + placed_row[i - 1][3]
                        if placed_row[i][1] < prev_right + 30:
                            placed_row[i][1] = _snap(prev_right + 40)
                    for nid, x, y, w, h in placed_row:
                        abs_boxes[nid] = (x, y, w, h)
                        rel_boxes[nid] = (x, y, w, h)
                        parent_map[nid] = "1"
                else:
                    tot_w = layer_widths[r]
                    cur_x = _snap(spine_cx - tot_w / 2)
                    for nid in nids:
                        w, h = boxes_wh[nid]
                        y = _snap(cur_y + (layer_heights[r] - h) / 2)
                        abs_boxes[nid] = (cur_x, y, w, h)
                        rel_boxes[nid] = (cur_x, y, w, h)
                        parent_map[nid] = "1"
                        cur_x += w + col_gap
                cur_y += layer_heights[r] + row_gap
        else:
            col_gap = 100
            row_gap = 70
            layer_widths = {}
            layer_heights = {}
            for r in range(max_rank + 1):
                nids = layers[r]
                if not nids:
                    layer_widths[r] = 140
                    layer_heights[r] = 0
                    continue
                layer_widths[r] = max(boxes_wh[n][0] for n in nids)
                layer_heights[r] = sum(boxes_wh[n][1] for n in nids) + row_gap * (len(nids) - 1)
            top_pad = 90 if back_edge_ids else 40
            spine_cy = _snap(margin_y + max(layer_heights.values(), default=220) / 2 + top_pad)

            cur_x = margin_x + 20
            for r in range(max_rank + 1):
                nids = layers[r]
                if not nids:
                    cur_x += 140
                    continue
                tot_h = layer_heights[r]
                cur_y = _snap(spine_cy - tot_h / 2)
                for nid in nids:
                    w, h = boxes_wh[nid]
                    x = _snap(cur_x + (layer_widths[r] - w) / 2)
                    abs_boxes[nid] = (x, cur_y, w, h)
                    rel_boxes[nid] = (x, cur_y, w, h)
                    parent_map[nid] = "1"
                    cur_y += h + row_gap
                cur_x += layer_widths[r] + col_gap

    # Determine which side(s) back-edges naturally occupy so annotations stay clear of loop corridors
    right_loop_nodes = set()
    left_loop_nodes = set()
    for e in raw_edges:
        if e["id"] in back_edge_ids and e["from"] in abs_boxes and e["to"] in abs_boxes:
            sb = abs_boxes[e["from"]]
            tb = abs_boxes[e["to"]]
            if sb[0] + sb[2] / 2.0 >= tb[0] + tb[2] / 2.0 - 20:
                right_loop_nodes.add(e["to"])
                right_loop_nodes.add(e["from"])
            else:
                left_loop_nodes.add(e["to"])
                left_loop_nodes.add(e["from"])

    # Place annotation nodes beside their attached target node, avoiding overlaps & loop corridors
    annot_side = {}
    max_right = max(
        [b[0] + b[2] for b in abs_boxes.values()] + [r[0] + r[2] for r in lane_abs_rects],
        default=600
    )
    min_left = min(
        [b[0] for b in abs_boxes.values()] + [r[0] for r in lane_abs_rects],
        default=margin_x
    )
    for idx, an in enumerate(annot_nodes):
        aid = an["id"]
        w, h = boxes_wh[aid]
        tgt_id = str(an.get("attach_to") or "")
        existing = list(abs_boxes.values())
        if tgt_id in abs_boxes:
            tx, ty, tw, th = abs_boxes[tgt_id]
            ay = _snap(ty + (th - h) / 2)
            if has_swimlanes:
                cand_positions = [
                    (_snap(max_right + 50), ay, "right"),
                    (_snap(min_left - w - 50), ay, "left"),
                ]
            else:
                prefer_left = (tgt_id in right_loop_nodes and tgt_id not in left_loop_nodes)
                right_pos = (_snap(tx + tw + 60), ay, "right")
                left_pos = (_snap(tx - w - 60), ay, "left")
                far_right = (_snap(max_right + 50), ay, "right")
                far_left = (_snap(min_left - w - 50), ay, "left")
                cand_positions = (
                    [left_pos, far_left, right_pos, far_right]
                    if prefer_left else
                    [right_pos, left_pos, far_right, far_left]
                )
            chosen = None
            for cx, cy, side in cand_positions:
                if has_swimlanes and cx < 20:
                    continue
                if not any(_boxes_overlap((cx, cy, w, h), eb, pad=10) for eb in existing):
                    chosen = (cx, cy, side)
                    break
            if chosen is None:
                ax, ay, side = _snap(max_right + 50), _snap(ay + idx * 80), "right"
            else:
                ax, ay, side = chosen
        else:
            ax, ay, side = _snap(max_right + 50), _snap(margin_y + idx * 90), "right"
            while any(_boxes_overlap((ax, ay, w, h), eb, pad=10) for eb in existing):
                ay += 80
        abs_boxes[aid] = (ax, ay, w, h)
        rel_boxes[aid] = (ax, ay, w, h)
        parent_map[aid] = "1"
        annot_side[aid] = side

    # Shift free-layout diagrams right if any node (including left annotations) is left of margin_x
    if not (has_swimlanes and lanes_spec):
        min_x_all = min((b[0] for b in abs_boxes.values()), default=margin_x)
        if min_x_all < margin_x:
            shift = _snap(margin_x - min_x_all + 20)
            for nid in list(abs_boxes):
                x, y, w, h = abs_boxes[nid]
                abs_boxes[nid] = (x + shift, y, w, h)
                rel_boxes[nid] = (x + shift, y, w, h)

    # Precompute swimlane border lines for W-ISO-SWIMLANE-CROSS avoidance
    lane_borders_x, lane_borders_y = [], []
    for lx, ly, lw, lh in lane_abs_rects:
        lane_borders_x.extend([lx, lx + lw])
        lane_borders_y.extend([ly, ly + lh])

    # Build XML tree
    mxfile = ET.Element("mxfile", host="pro-diagrams", version="1.0.0")
    diagram = ET.SubElement(mxfile, "diagram", id="page-1", name=spec.get("page_name") or "ISO-5807-Diagram")
    bg_hex = _safe_style_val(preset_extras.get("background", "#F8F6F2"))
    all_r = [b[0] + b[2] for b in abs_boxes.values()] + [lc[2] + lc[4] for lc in lane_cells if lc[6] == "1"]
    all_b = [b[1] + b[3] for b in abs_boxes.values()] + [lc[3] + lc[5] for lc in lane_cells if lc[6] == "1"]
    page_w = max(900, _snap(max(all_r, default=800) + 140))
    page_h = max(640, _snap(max(all_b, default=560) + 100))

    model = ET.SubElement(
        diagram, "mxGraphModel",
        dx="1280", dy="800", grid="1", gridSize="10", guides="1", tooltips="1",
        connect="1", arrows="1", fold="1", page="1", pageScale="1",
        pageWidth=str(page_w), pageHeight=str(page_h),
        background=bg_hex, math="0", shadow="0"
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    # Title & subtitle cells (exempted chrome)
    title_x = _snap(margin_x)
    title_w = max(400, page_w - 2 * title_x)
    title_h = header_h - 10
    title_box = (title_x, 20, title_w, title_h)
    ink_muted = _safe_style_val(theme_tok["ink_muted"])
    ink_heading = _safe_style_val(theme_tok["ink_heading"])
    title_html = f"<b>{html.escape(title)}</b>"
    if subtitle:
        title_html += f"<br/><font style='font-size:11px;color:{ink_muted}'>{html.escape(subtitle)}</font>"
    title_cell = ET.SubElement(
        root, "mxCell", id="title_banner", value=title_html,
        style=(
            f"text;html=1;align=left;verticalAlign=middle;whiteSpace=wrap;"
            f"fillColor=none;strokeColor=none;fontFamily={font_family};fontSize=16;"
            f"fontColor={ink_heading};"
        ),
        vertex="1", parent="1"
    )
    ET.SubElement(title_cell, "mxGeometry", attrib={
        "x": str(title_x), "y": "20",
        "width": str(title_w), "height": str(title_h),
        "as": "geometry"
    })

    # Emit Pool & Swimlanes
    for lid, ltitle, lx, ly, lw, lh, lparent, lstyle in lane_cells:
        lc = ET.SubElement(root, "mxCell", id=lid, value=ltitle, style=lstyle, vertex="1", parent=lparent)
        ET.SubElement(lc, "mxGeometry", attrib={
            "x": str(lx), "y": str(ly), "width": str(lw), "height": str(lh), "as": "geometry"
        })

    # Emit Flow & Annotation Vertices
    for n in flow_nodes + annot_nodes:
        nid = n["id"]
        sym_key = n["type"]
        sinfo = sym_catalog.get(sym_key) or sym_catalog["process"]
        base_style = sinfo["drawio_style"]
        slot = n.get("slot") or sinfo.get("theme_slot", "neutral")
        if nid in crit_nodes:
            slot = "accent"
        pair = palette.get(slot) or palette["neutral"]
        fill_c = _safe_style_val(pair["fillColor"])
        stroke_c = _safe_style_val(pair["strokeColor"])
        sw_val = 2.5 if nid in crit_nodes else stroke_w

        if sym_key == "annotation":
            flip_part = "flipH=1;" if annot_side.get(nid) == "left" else ""
            full_style = (
                f"{base_style}{flip_part}fillColor=none;strokeColor={ink_muted};"
                f"fontColor={ink_muted};fontFamily={font_family};fontSize=11;"
                f"spacingLeft=8;spacingTop=4;spacingBottom=4;strokeWidth=1.2;"
            )
        else:
            bold_part = "fontStyle=1;" if sym_key in ("terminator", "decision") else ""
            full_style = (
                f"{base_style}fillColor={fill_c};strokeColor={stroke_c};"
                f"fontColor={font_color};fontFamily={font_family};fontSize={font_size};{bold_part}"
                f"strokeWidth={sw_val:g};spacingTop=6;spacingBottom=6;spacingLeft=8;spacingRight=8;"
            )
        rx, ry, w, h = rel_boxes[nid]
        cell = ET.SubElement(
            root, "mxCell", id=nid, value=formatted_labels[nid],
            style=full_style, vertex="1", parent=parent_map[nid]
        )
        ET.SubElement(cell, "mxGeometry", attrib={
            "x": str(rx), "y": str(ry), "width": str(w), "height": str(h), "as": "geometry"
        })

    # Emit dashed annotation connector lines
    annot_edge_seq = 1
    for an in annot_nodes:
        tgt_id = str(an.get("attach_to") or "")
        if tgt_id in abs_boxes:
            while f"annot_edge_{annot_edge_seq}" in used_ids:
                annot_edge_seq += 1
            aeid = f"annot_edge_{annot_edge_seq}"
            used_ids.add(aeid)
            annot_edge_seq += 1
            if annot_side.get(an["id"]) == "left":
                port_part = "exitX=1;exitY=0.5;entryX=0;entryY=0.5;"
            else:
                port_part = "exitX=0;exitY=0.5;entryX=1;entryY=0.5;"
            ec = ET.SubElement(
                root, "mxCell", id=aeid, value="",
                style=(
                    f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;dashed=1;"
                    f"endArrow=none;strokeColor={ink_muted};strokeWidth=1.2;"
                    f"{port_part}"
                ),
                edge="1", parent="1", source=an["id"], target=tgt_id
            )
            ET.SubElement(ec, "mxGeometry", attrib={"relative": "1", "as": "geometry"})

    # Group outgoing & incoming flow edges for clean port allocation & routing
    out_by_src = defaultdict(list)
    in_by_tgt = defaultdict(list)
    valid_edges = []
    for e in raw_edges:
        if e["from"] in abs_boxes and e["to"] in abs_boxes:
            valid_edges.append(e)
            out_by_src[e["from"]].append(e)
            in_by_tgt[e["to"]].append(e)

    # Precompute bounding box and node-free inter-rank gap channels
    min_box_x = min((b[0] for b in abs_boxes.values()), default=100)
    max_box_x = max((b[0] + b[2] for b in abs_boxes.values()), default=700)
    min_box_y = min((b[1] for b in abs_boxes.values()), default=120)
    max_box_y = max((b[1] + b[3] for b in abs_boxes.values()), default=500)
    if lane_abs_rects:
        min_box_x = min(min_box_x, min(r[0] for r in lane_abs_rects))
        max_box_x = max(max_box_x, max(r[0] + r[2] for r in lane_abs_rects))
        min_box_y = min(min_box_y, min(r[1] for r in lane_abs_rects))
        max_box_y = max(max_box_y, max(r[1] + r[3] for r in lane_abs_rects))

    # Compute clean inter-rank horizontal (TB) and vertical (LR) gap channels
    rank_y_bands = {}
    rank_x_bands = {}
    for nid, (bx, by, bw, bh) in abs_boxes.items():
        if nid not in ranks:
            continue
        r = ranks[nid]
        if r not in rank_y_bands:
            rank_y_bands[r] = [by, by + bh]
            rank_x_bands[r] = [bx, bx + bw]
        else:
            rank_y_bands[r][0] = min(rank_y_bands[r][0], by)
            rank_y_bands[r][1] = max(rank_y_bands[r][1], by + bh)
            rank_x_bands[r][0] = min(rank_x_bands[r][0], bx)
            rank_x_bands[r][1] = max(rank_x_bands[r][1], bx + bw)

    gap_ys = []
    sorted_r = sorted(rank_y_bands)
    for r_prev, r_next in zip(sorted_r, sorted_r[1:]):
        y_lo, y_hi = rank_y_bands[r_prev][1], rank_y_bands[r_next][0]
        if y_hi - y_lo >= 20:
            gap_ys.append(_avoid_border((y_lo + y_hi) / 2.0, lane_borders_y))
    if sorted_r:
        top_gap = _avoid_border(rank_y_bands[sorted_r[0]][0] - 25, lane_borders_y)
        if top_gap > title_box[1] + title_box[3] + 10:
            gap_ys.append(top_gap)
        gap_ys.append(_avoid_border(rank_y_bands[sorted_r[-1]][1] + 30, lane_borders_y))

    gap_xs = []
    for r_prev, r_next in zip(sorted_r, sorted_r[1:]):
        x_lo, x_hi = rank_x_bands[r_prev][1], rank_x_bands[r_next][0]
        if x_hi - x_lo >= 20:
            gap_xs.append(_avoid_border((x_lo + x_hi) / 2.0, lane_borders_x))

    # Assign exits for Decision nodes geometrically (avoiding crossed/backward exits)
    decision_ports = {}
    for nid, outs in out_by_src.items():
        if by_node.get(nid, {}).get("type") != "decision":
            continue
        sx, sy, sw, sh = abs_boxes[nid]
        scx, scy = sx + sw / 2.0, sy + sh / 2.0
        fwd_outs = [e for e in outs if e["id"] not in back_edge_ids]
        back_outs = [e for e in outs if e["id"] in back_edge_ids]
        used_sides = set()

        if direction == "TB":
            # Assign directly-below forward target to bottom first so it never wraps around
            below_cands = [
                e for e in fwd_outs
                if abs((abs_boxes[e["to"]][0] + abs_boxes[e["to"]][2] / 2.0) - scx) <= 25
                and (abs_boxes[e["to"]][1] + abs_boxes[e["to"]][3] / 2.0) >= scy
            ]
            if below_cands:
                # Prefer affirmative among directly-below targets
                below_cands.sort(key=lambda e: (0 if _is_affirmative_label(e["label"]) else 1))
                chosen_bot = below_cands[0]
                decision_ports[chosen_bot["id"]] = (0.5, 1.0)
                used_sides.add("bottom")

            # Remaining forward edges: route left targets via left, right via right, or affirmative via bottom
            rem_fwd = [e for e in fwd_outs if e["id"] not in decision_ports]
            rem_fwd.sort(key=lambda e: (abs_boxes[e["to"]][0] + abs_boxes[e["to"]][2] / 2.0))
            for e in rem_fwd:
                eid = e["id"]
                tx, ty, tw, th = abs_boxes[e["to"]]
                tcx, tcy = tx + tw / 2.0, ty + th / 2.0
                if tcx < scx - 25 and "left" not in used_sides:
                    decision_ports[eid] = (0.0, 0.5)
                    used_sides.add("left")
                elif tcx > scx + 25 and "right" not in used_sides:
                    decision_ports[eid] = (1.0, 0.5)
                    used_sides.add("right")
                elif _is_affirmative_label(e["label"]) and "bottom" not in used_sides and tcy >= scy:
                    decision_ports[eid] = (0.5, 1.0)
                    used_sides.add("bottom")
                elif "bottom" not in used_sides and tcy >= scy:
                    decision_ports[eid] = (0.5, 1.0)
                    used_sides.add("bottom")
                elif "right" not in used_sides:
                    decision_ports[eid] = (1.0, 0.5)
                    used_sides.add("right")
                elif "left" not in used_sides:
                    decision_ports[eid] = (0.0, 0.5)
                    used_sides.add("left")
                else:
                    decision_ports[eid] = (0.5, 1.0)

            for e in back_outs:
                eid = e["id"]
                tx, ty, tw, th = abs_boxes[e["to"]]
                tcx = tx + tw / 2.0
                if tcx < scx - 25 and "left" not in used_sides:
                    decision_ports[eid] = (0.0, 0.5)
                    used_sides.add("left")
                elif "right" not in used_sides:
                    decision_ports[eid] = (1.0, 0.5)
                    used_sides.add("right")
                elif "left" not in used_sides:
                    decision_ports[eid] = (0.0, 0.5)
                    used_sides.add("left")
                else:
                    decision_ports[eid] = (1.0, 0.5)
        else:
            right_cands = [
                e for e in fwd_outs
                if abs((abs_boxes[e["to"]][1] + abs_boxes[e["to"]][3] / 2.0) - scy) <= 25
                and (abs_boxes[e["to"]][0] + abs_boxes[e["to"]][2] / 2.0) >= scx
            ]
            if right_cands:
                right_cands.sort(key=lambda e: (0 if _is_affirmative_label(e["label"]) else 1))
                chosen_r = right_cands[0]
                decision_ports[chosen_r["id"]] = (1.0, 0.5)
                used_sides.add("right")

            rem_fwd = [e for e in fwd_outs if e["id"] not in decision_ports]
            rem_fwd.sort(key=lambda e: (abs_boxes[e["to"]][1] + abs_boxes[e["to"]][3] / 2.0))
            for e in rem_fwd:
                eid = e["id"]
                tx, ty, tw, th = abs_boxes[e["to"]]
                tcx, tcy = tx + tw / 2.0, ty + th / 2.0
                if tcy < scy - 25 and "top" not in used_sides:
                    decision_ports[eid] = (0.5, 0.0)
                    used_sides.add("top")
                elif tcy > scy + 25 and "bottom" not in used_sides:
                    decision_ports[eid] = (0.5, 1.0)
                    used_sides.add("bottom")
                elif _is_affirmative_label(e["label"]) and "right" not in used_sides and tcx >= scx:
                    decision_ports[eid] = (1.0, 0.5)
                    used_sides.add("right")
                elif "right" not in used_sides and tcx >= scx:
                    decision_ports[eid] = (1.0, 0.5)
                    used_sides.add("right")
                elif "bottom" not in used_sides:
                    decision_ports[eid] = (0.5, 1.0)
                    used_sides.add("bottom")
                elif "top" not in used_sides:
                    decision_ports[eid] = (0.5, 0.0)
                    used_sides.add("top")
                else:
                    decision_ports[eid] = (1.0, 0.5)

            for e in back_outs:
                eid = e["id"]
                tx, ty, tw, th = abs_boxes[e["to"]]
                tcy = ty + th / 2.0
                if tcy < scy - 25 and "top" not in used_sides:
                    decision_ports[eid] = (0.5, 0.0)
                    used_sides.add("top")
                elif "bottom" not in used_sides:
                    decision_ports[eid] = (0.5, 1.0)
                    used_sides.add("bottom")
                elif "top" not in used_sides:
                    decision_ports[eid] = (0.5, 0.0)
                    used_sides.add("top")
                else:
                    decision_ports[eid] = (0.5, 1.0)

    # Candidate route generator & multi-criteria obstacle/crossing-free selector
    def _route_edge(e, loop_slot, waypointed_routes, straight_routes):
        eid, u, v = e["id"], e["from"], e["to"]
        sx, sy, sw, sh = abs_boxes[u]
        tx, ty, tw, th = abs_boxes[v]
        scx, scy = sx + sw / 2.0, sy + sh / 2.0
        tcx, tcy = tx + tw / 2.0, ty + th / 2.0
        is_back = eid in back_edge_ids
        other_boxes = [b for k, b in abs_boxes.items() if k not in (u, v)] + [title_box]

        candidates = []

        def _add_cand(ex_x, ex_y, en_x, en_y, wps, require_wps=False):
            clean_wps = _dedupe_waypoints(wps)
            if require_wps and not clean_wps:
                return
            p1 = (sx + ex_x * sw, sy + ex_y * sh)
            p2 = (tx + en_x * tw, ty + en_y * th)
            full = [p1] + clean_wps + [p2]
            if not _valid_port_directions(full, ex_x, ex_y, en_x, en_y):
                return
            candidates.append((ex_x, ex_y, en_x, en_y, clean_wps, full))

        if is_back:
            if direction == "TB":
                pref_port = decision_ports.get(eid)
                exit_ports = [pref_port] if pref_port else [(1.0, 0.5), (0.0, 0.5), (0.5, 1.0), (0.5, 0.0)]
                if pref_port and pref_port[0] == 0.5:
                    exit_ports = [(1.0, 0.5), (0.0, 0.5), pref_port]
                elif pref_port:
                    alt = (0.0, 0.5) if pref_port[0] == 1.0 else (1.0, 0.5)
                    exit_ports = [pref_port, alt]

                corridor_xs_right = [
                    _avoid_border(max_box_x + 50 + 30 * (loop_slot + k), lane_borders_x)
                    for k in range(3)
                ]
                corridor_xs_left = [
                    _avoid_border(min_box_x - 50 - 30 * (loop_slot + k), lane_borders_x)
                    for k in range(3)
                ]
                local_right = _avoid_border(max(sx + sw, tx + tw) + 35 + 20 * loop_slot, lane_borders_x)
                local_left = _avoid_border(min(sx, tx) - 35 - 20 * loop_slot, lane_borders_x)

                src_gap_ys = [_avoid_border(sy + sh + 25, lane_borders_y), _avoid_border(sy - 25, lane_borders_y)]
                tgt_gap_ys = [_avoid_border(ty - 25, lane_borders_y), _avoid_border(ty + th + 25, lane_borders_y)]
                for gy in gap_ys:
                    if abs(gy - (sy + sh)) < 55 or abs(gy - sy) < 55:
                        src_gap_ys.append(gy)
                    if abs(gy - ty) < 55 or abs(gy - (ty + th)) < 55:
                        tgt_gap_ys.append(gy)

                for side_name, cxs in (("right", [local_right] + corridor_xs_right),
                                       ("left", [local_left] + corridor_xs_left)):
                    ex_side = (1.0, 0.5) if side_name == "right" else (0.0, 0.5)
                    en_side = (1.0, 0.5) if side_name == "right" else (0.0, 0.5)
                    for cx in cxs:
                        if cx < 20:
                            continue
                        # Pattern 1: direct U-turn side-to-side
                        if ex_side in exit_ports or not pref_port:
                            p_sy = _snap(sy + 0.5 * sh)
                            p_ey = _snap(ty + 0.5 * th)
                            _add_cand(ex_side[0], ex_side[1], en_side[0], en_side[1],
                                      [(cx, p_sy), (cx, p_ey)], require_wps=True)
                        # Pattern 2: exit via gap below/above u -> corridor -> enter side of v
                        for gy_s in src_gap_ys:
                            ex_v = (0.5, 1.0) if gy_s >= sy + sh else (0.5, 0.0)
                            if pref_port and ex_v != pref_port:
                                # Also allow short side jog from decision port into gap
                                jx = _avoid_border((sx + sw + 25) if pref_port[0] == 1.0 else (sx - 25), lane_borders_x)
                                _add_cand(pref_port[0], pref_port[1], en_side[0], en_side[1],
                                          [(jx, _snap(sy + 0.5 * sh)), (jx, gy_s), (cx, gy_s), (cx, _snap(ty + 0.5 * th))],
                                          require_wps=True)
                            else:
                                _add_cand(ex_v[0], ex_v[1], en_side[0], en_side[1],
                                          [(_snap(scx), gy_s), (cx, gy_s), (cx, _snap(ty + 0.5 * th))],
                                          require_wps=True)
                        # Pattern 3: exit side of u -> corridor -> enter target via gap above/below v
                        for gy_t in tgt_gap_ys:
                            en_v = (0.75 if side_name == "right" else 0.25, 0.0 if gy_t <= ty else 1.0)
                            if ex_side in exit_ports or not pref_port:
                                _add_cand(ex_side[0], ex_side[1], en_v[0], en_v[1],
                                          [(cx, _snap(sy + 0.5 * sh)), (cx, gy_t), (_snap(tx + en_v[0] * tw), gy_t)],
                                          require_wps=True)
                        # Pattern 4: both source & target use gap doglegs
                        for gy_s in src_gap_ys[:2]:
                            ex_v = (0.5, 1.0) if gy_s >= sy + sh else (0.5, 0.0)
                            if pref_port and ex_v != pref_port:
                                continue
                            for gy_t in tgt_gap_ys[:2]:
                                en_v = (0.75 if side_name == "right" else 0.25, 0.0 if gy_t <= ty else 1.0)
                                _add_cand(ex_v[0], ex_v[1], en_v[0], en_v[1],
                                          [(_snap(scx), gy_s), (cx, gy_s), (cx, gy_t), (_snap(tx + en_v[0] * tw), gy_t)],
                                          require_wps=True)
            else:
                # LR back-edge
                pref_port = decision_ports.get(eid)
                corridor_ys_bot = [
                    _avoid_border(max_box_y + 45 + 30 * (loop_slot + k), lane_borders_y)
                    for k in range(3)
                ]
                corridor_ys_top = [
                    _avoid_border(min_box_y - 45 - 30 * (loop_slot + k), lane_borders_y)
                    for k in range(3)
                ]
                local_bot = _avoid_border(max(sy + sh, ty + th) + 35 + 20 * loop_slot, lane_borders_y)
                local_top = _avoid_border(min(sy, ty) - 35 - 20 * loop_slot, lane_borders_y)
                min_safe_y = title_box[1] + title_box[3] + 15

                for side_name, cys in (("bottom", [local_bot] + corridor_ys_bot),
                                       ("top", [local_top] + corridor_ys_top)):
                    ex_side = (0.5, 1.0) if side_name == "bottom" else (0.5, 0.0)
                    en_side = (0.5, 1.0) if side_name == "bottom" else (0.5, 0.0)
                    for cy in cys:
                        if cy < min_safe_y:
                            continue
                        _add_cand(ex_side[0], ex_side[1], en_side[0], en_side[1],
                                  [(_snap(scx), cy), (_snap(tcx), cy)], require_wps=True)
                        # Exit right or left into inter-rank gap -> corridor -> enter side
                        gx_sr = _avoid_border(sx + sw + 25, lane_borders_x)
                        gx_sl = _avoid_border(sx - 25, lane_borders_x)
                        gx_t = _avoid_border(tx - 25, lane_borders_x)
                        en_v = (0.0, 0.75 if side_name == "bottom" else 0.25)
                        _add_cand(1.0, 0.5, en_side[0], en_side[1],
                                  [(gx_sr, _snap(scy)), (gx_sr, cy), (_snap(tcx), cy)], require_wps=True)
                        _add_cand(0.0, 0.5, en_side[0], en_side[1],
                                  [(gx_sl, _snap(scy)), (gx_sl, cy), (_snap(tcx), cy)], require_wps=True)
                        _add_cand(ex_side[0], ex_side[1], en_v[0], en_v[1],
                                  [(_snap(scx), cy), (gx_t, cy), (gx_t, _snap(ty + en_v[1] * th))], require_wps=True)
                        _add_cand(1.0, 0.5, en_v[0], en_v[1],
                                  [(gx_sr, _snap(scy)), (gx_sr, cy), (gx_t, cy), (gx_t, _snap(ty + en_v[1] * th))], require_wps=True)
                        _add_cand(0.0, 0.5, en_v[0], en_v[1],
                                  [(gx_sl, _snap(scy)), (gx_sl, cy), (gx_t, cy), (gx_t, _snap(ty + en_v[1] * th))], require_wps=True)
        else:
            # Forward edge
            if direction == "TB":
                if eid in decision_ports:
                    ex_x, ex_y = decision_ports[eid]
                else:
                    fwd_outs = [oe for oe in out_by_src[u] if oe["id"] not in back_edge_ids]
                    if len(fwd_outs) > 1:
                        fwd_outs_sorted = sorted(
                            fwd_outs,
                            key=lambda oe: (abs_boxes[oe["to"]][0] + abs_boxes[oe["to"]][2] / 2.0, oe["id"])
                        )
                        k_idx = fwd_outs_sorted.index(e)
                        ex_x = round((k_idx + 1) / (len(fwd_outs_sorted) + 1), 4)
                    else:
                        ex_x = 0.5
                    ex_y = 1.0

                fwd_ins = [ie for ie in in_by_tgt[v] if ie["id"] not in back_edge_ids]
                if ex_y == 0.5 and abs(tcy - scy) < 35:
                    en_x = 0.0 if tcx > scx else 1.0
                    en_y = 0.5
                else:
                    if len(fwd_ins) > 1:
                        fwd_ins_sorted = sorted(
                            fwd_ins,
                            key=lambda ie: (abs_boxes[ie["from"]][0] + abs_boxes[ie["from"]][2] / 2.0, ie["id"])
                        )
                        k_in = fwd_ins_sorted.index(e)
                        en_x = round(0.25 + 0.5 * (k_in / max(1, len(fwd_ins_sorted) - 1)), 4)
                    else:
                        en_x = 0.5
                    en_y = 0.0

                px1, py1 = sx + ex_x * sw, sy + ex_y * sh
                px2, py2 = tx + en_x * tw, ty + en_y * th
                going_upward = tcy < sy - 10  # needs waypoints for W-ISO-FLOW-DIR

                if ex_y == 0.5 and en_y == 0.5:
                    # Same-rank horizontal jump
                    _add_cand(ex_x, ex_y, en_x, en_y, [])
                elif ex_y == 0.5 and en_y == 0.0:
                    # Side exit from decision -> L-bend into target top
                    _add_cand(ex_x, ex_y, en_x, en_y, [(_snap(px2), _snap(py1))])
                    # Z-bends via side channel into inter-rank gap above target
                    side_dir = 1 if ex_x > 0.5 else -1
                    for off_x in (30, 50, 70):
                        sx_ch = _avoid_border(px1 + side_dir * off_x, lane_borders_x)
                        for off_y in (25, 35, 15):
                            my = _avoid_border(py2 - off_y, lane_borders_y)
                            _add_cand(ex_x, ex_y, en_x, en_y, [(sx_ch, _snap(py1)), (sx_ch, my), (_snap(px2), my)])
                        # Also try entering target side directly
                        side_en_x = 0.0 if sx_ch < tx else 1.0
                        _add_cand(ex_x, ex_y, side_en_x, 0.5, [(sx_ch, _snap(py1)), (sx_ch, _snap(tcy))])
                elif abs(px1 - px2) <= 4 and not going_upward:
                    # Straight vertical candidate (no waypoints if obstacle-free)
                    if not _route_hits_any_box([(px1, py1), (px2, py2)], other_boxes, pad=2):
                        _add_cand(ex_x, ex_y, en_x, en_y, [])
                    else:
                        for dx_c in (
                            _avoid_border(max_box_x + 40, lane_borders_x),
                            _avoid_border(min_box_x - 40, lane_borders_x),
                            _avoid_border(max(sx + sw, tx + tw) + 35, lane_borders_x),
                            _avoid_border(min(sx, tx) - 35, lane_borders_x),
                        ):
                            if dx_c >= 20:
                                _add_cand(ex_x, ex_y, en_x, en_y, [
                                    (_snap(px1), _avoid_border(py1 + 20, lane_borders_y)),
                                    (dx_c, _avoid_border(py1 + 20, lane_borders_y)),
                                    (dx_c, _avoid_border(py2 - 25, lane_borders_y)),
                                    (_snap(px2), _avoid_border(py2 - 25, lane_borders_y)),
                                ])
                else:
                    # Multi-column Z-bend: try midpoint, early gap, late gap, and all intermediate rank gaps
                    cand_ys = [
                        _avoid_border((py1 + py2) / 2.0, lane_borders_y),
                        _avoid_border(py1 + 25, lane_borders_y),
                        _avoid_border(py1 + 35, lane_borders_y),
                        _avoid_border(py2 - 25, lane_borders_y),
                        _avoid_border(py2 - 35, lane_borders_y),
                    ]
                    for gy in gap_ys:
                        if min(py1, py2) + 8 < gy < max(py1, py2) - 8:
                            cand_ys.append(gy)
                    seen_y = set()
                    for my in cand_ys:
                        if my in seen_y:
                            continue
                        seen_y.add(my)
                        _add_cand(ex_x, ex_y, en_x, en_y, [(_snap(px1), my), (_snap(px2), my)],
                                  require_wps=going_upward)
                    # Try L-bend entering side of target (clean for swimlane handoffs)
                    side_en_x = 0.0 if px1 < tx else 1.0
                    _add_cand(ex_x, ex_y, side_en_x, 0.5, [(_snap(px1), _snap(tcy))], require_wps=going_upward)
                    # Outer / local vertical detours if direct Z-bends hit intermediate nodes or edges
                    for dx_c in (
                        _avoid_border(max_box_x + 40 + 20 * loop_slot, lane_borders_x),
                        _avoid_border(min_box_x - 40 - 20 * loop_slot, lane_borders_x),
                    ):
                        if dx_c >= 20:
                            y_s = _avoid_border(py1 + 20, lane_borders_y)
                            y_e = _avoid_border(py2 - 25, lane_borders_y)
                            _add_cand(ex_x, ex_y, en_x, en_y, [
                                (_snap(px1), y_s), (dx_c, y_s), (dx_c, y_e), (_snap(px2), y_e)
                            ], require_wps=True)
            else:
                # LR forward routing
                if eid in decision_ports:
                    ex_x, ex_y = decision_ports[eid]
                else:
                    fwd_outs = [oe for oe in out_by_src[u] if oe["id"] not in back_edge_ids]
                    if len(fwd_outs) > 1:
                        fwd_outs_sorted = sorted(
                            fwd_outs,
                            key=lambda oe: (abs_boxes[oe["to"]][1] + abs_boxes[oe["to"]][3] / 2.0, oe["id"])
                        )
                        k_idx = fwd_outs_sorted.index(e)
                        ex_y = round(0.25 + 0.5 * (k_idx / max(1, len(fwd_outs_sorted) - 1)), 4)
                    else:
                        ex_y = 0.5
                    ex_x = 1.0

                fwd_ins = [ie for ie in in_by_tgt[v] if ie["id"] not in back_edge_ids]
                if len(fwd_ins) > 1:
                    fwd_ins_sorted = sorted(
                        fwd_ins,
                        key=lambda ie: (abs_boxes[ie["from"]][1] + abs_boxes[ie["from"]][3] / 2.0, ie["id"])
                    )
                    k_in = fwd_ins_sorted.index(e)
                    en_y = round(0.25 + 0.5 * (k_in / max(1, len(fwd_ins_sorted) - 1)), 4)
                else:
                    en_y = 0.5
                en_x = 0.0

                px1, py1 = sx + ex_x * sw, sy + ex_y * sh
                px2, py2 = tx + en_x * tw, ty + en_y * th
                going_left = tcx < sx - 10

                if ex_x == 0.5 and en_x == 0.0:
                    _add_cand(ex_x, ex_y, en_x, en_y, [(_snap(px1), _snap(py2))])
                    side_dir = 1 if ex_y > 0.5 else -1
                    for off_y in (30, 50, 70):
                        sy_ch = _avoid_border(py1 + side_dir * off_y, lane_borders_y)
                        for off_x in (25, 35):
                            mx = _avoid_border(px2 - off_x, lane_borders_x)
                            _add_cand(ex_x, ex_y, en_x, en_y, [(_snap(px1), sy_ch), (mx, sy_ch), (mx, _snap(py2))])
                        side_en_y = 0.0 if sy_ch < ty else 1.0
                        _add_cand(ex_x, ex_y, 0.5, side_en_y, [(_snap(px1), sy_ch), (_snap(tcx), sy_ch)])
                elif abs(py1 - py2) <= 4 and not going_left:
                    if not _route_hits_any_box([(px1, py1), (px2, py2)], other_boxes, pad=2):
                        _add_cand(ex_x, ex_y, en_x, en_y, [])
                    else:
                        for dy_c in (
                            _avoid_border(max_box_y + 40, lane_borders_y),
                            _avoid_border(min_box_y - 40, lane_borders_y),
                        ):
                            if dy_c > title_box[1] + title_box[3] + 15:
                                _add_cand(ex_x, ex_y, en_x, en_y, [
                                    (_avoid_border(px1 + 20, lane_borders_x), _snap(py1)),
                                    (_avoid_border(px1 + 20, lane_borders_x), dy_c),
                                    (_avoid_border(px2 - 25, lane_borders_x), dy_c),
                                    (_avoid_border(px2 - 25, lane_borders_x), _snap(py2)),
                                ])
                else:
                    cand_xs = [
                        _avoid_border((px1 + px2) / 2.0, lane_borders_x),
                        _avoid_border(px1 + 25, lane_borders_x),
                        _avoid_border(px2 - 25, lane_borders_x),
                    ]
                    for gx in gap_xs:
                        if min(px1, px2) + 8 < gx < max(px1, px2) - 8:
                            cand_xs.append(gx)
                    seen_x = set()
                    for mx in cand_xs:
                        if mx in seen_x:
                            continue
                        seen_x.add(mx)
                        _add_cand(ex_x, ex_y, en_x, en_y, [(mx, _snap(py1)), (mx, _snap(py2))],
                                  require_wps=going_left)
                    side_en_y = 0.0 if py1 < ty else 1.0
                    _add_cand(ex_x, ex_y, 0.5, side_en_y, [(_snap(tcx), _snap(py1))], require_wps=going_left)
                    for dy_c in (
                        _avoid_border(max_box_y + 40 + 20 * loop_slot, lane_borders_y),
                        _avoid_border(min_box_y - 40 - 20 * loop_slot, lane_borders_y),
                    ):
                        if dy_c > title_box[1] + title_box[3] + 15:
                            x_s = _avoid_border(px1 + 20, lane_borders_x)
                            x_e = _avoid_border(px2 - 25, lane_borders_x)
                            _add_cand(ex_x, ex_y, en_x, en_y, [
                                (x_s, _snap(py1)), (x_s, dy_c), (x_e, dy_c), (x_e, _snap(py2))
                            ], require_wps=True)

        if not candidates:
            # Safe fallback
            ex_x, ex_y = (0.5, 1.0) if direction == "TB" else (1.0, 0.5)
            en_x, en_y = (0.5, 0.0) if direction == "TB" else (0.0, 0.5)
            p1 = (sx + ex_x * sw, sy + ex_y * sh)
            p2 = (tx + en_x * tw, ty + en_y * th)
            return ex_x, ex_y, en_x, en_y, [], [p1, p2]

        def _score_cand(cand):
            _, _, _, _, wps, full = cand
            # Exact validate.py checks (only apply to waypointed edges for crossing/through-vertex)
            exact_hits = _count_route_box_hits(full, other_boxes, pad=0)
            pad_hits = _count_route_box_hits(full, other_boxes, pad=4)
            hard_cross = 0
            if wps:
                for oid, opt in waypointed_routes.items():
                    if oid != eid and _routes_cross(full, opt):
                        hard_cross += 1
            soft_cross = 0
            for oid, opt in straight_routes.items():
                if oid != eid and _routes_cross(full, opt):
                    soft_cross += 1
            border_hits = _count_border_hits(full, lane_borders_x, lane_borders_y)
            return (exact_hits, hard_cross, border_hits, pad_hits, soft_cross, len(wps), _manhattan_len(full))

        best = min(candidates, key=_score_cand)
        return best

    # Route short forward edges -> long forward edges -> back-edges, then refine any conflicts
    def _edge_priority(e):
        is_b = 1 if e["id"] in back_edge_ids else 0
        span = abs(ranks.get(e["to"], 0) - ranks.get(e["from"], 0))
        return (is_b, span, valid_edges.index(e))

    ordered_edges = sorted(valid_edges, key=_edge_priority)
    routed_results = {}     # eid -> (ex_x, ex_y, en_x, en_y, wps, full)
    waypointed_routes = {}  # eid -> full polyline (for edges with waypoints)
    straight_routes = {}    # eid -> full polyline (for edges without waypoints)
    loop_slots = {}
    loop_counter = 0

    for e in ordered_edges:
        eid = e["id"]
        if eid in back_edge_ids:
            loop_slots[eid] = loop_counter
            loop_counter += 1
        else:
            loop_slots[eid] = 0
        res = _route_edge(e, loop_slots[eid], waypointed_routes, straight_routes)
        routed_results[eid] = res
        if res[4]:
            waypointed_routes[eid] = res[5]
        else:
            straight_routes[eid] = res[5]

    # Pass 2 refinement: if any routed edge still has a crossing or vertex hit, re-route it
    for _ in range(2):
        changed = False
        for e in ordered_edges:
            eid, u, v = e["id"], e["from"], e["to"]
            ex_x, ex_y, en_x, en_y, wps, full = routed_results[eid]
            if not wps:
                continue
            other_boxes = [b for k, b in abs_boxes.items() if k not in (u, v)] + [title_box]
            has_issue = (
                _count_route_box_hits(full, other_boxes, pad=0) > 0
                or _count_border_hits(full, lane_borders_x, lane_borders_y) > 0
                or any(oid != eid and _routes_cross(full, opt) for oid, opt in waypointed_routes.items())
            )
            if has_issue:
                new_res = _route_edge(e, loop_slots[eid] + 1, waypointed_routes, straight_routes)
                if new_res[4] != wps or new_res[0:4] != (ex_x, ex_y, en_x, en_y):
                    routed_results[eid] = new_res
                    if new_res[4]:
                        waypointed_routes[eid] = new_res[5]
                        straight_routes.pop(eid, None)
                    else:
                        waypointed_routes.pop(eid, None)
                        straight_routes[eid] = new_res[5]
                    changed = True
        if not changed:
            break

    # Emit Flow Edges in original spec order
    edge_base_color = _safe_style_val(preset_extras.get("edgeColor", theme_tok["edge_stroke"]))
    edge_crit_color = _safe_style_val(theme_tok["edge_critical"])
    edge_err_color = _safe_style_val(palette["danger"]["strokeColor"])
    edge_label_bg = _safe_style_val(theme_tok["edge_label_bg"])

    for e in valid_edges:
        eid, u, v = e["id"], e["from"], e["to"]
        ex_x, ex_y, en_x, en_y, waypoints, _ = routed_results[eid]
        is_back = eid in back_edge_ids
        is_crit_edge = (eid in crit_edges) or (e["style_role"] == "critical")
        ecolor = edge_crit_color if is_crit_edge else (
            edge_err_color if e["style_role"] == "error" else edge_base_color
        )
        ewidth = 2.4 if is_crit_edge else 1.5
        dash_part = "dashed=1;" if (e["dashed"] or (is_back and spec.get("dash_back_edges", False))) else ""
        est = (
            f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
            f"exitX={ex_x:g};exitY={ex_y:g};exitDx=0;exitDy=0;"
            f"entryX={en_x:g};entryY={en_y:g};entryDx=0;entryDy=0;"
            f"endArrow=block;endFill=1;endSize=7;strokeColor={ecolor};strokeWidth={ewidth:g};{dash_part}"
            f"fontFamily={font_family};fontSize=11;fontColor={ecolor};"
            f"labelBackgroundColor={edge_label_bg};"
        )
        ec = ET.SubElement(
            root, "mxCell", id=eid, value=html.escape(e["label"]),
            style=est, edge="1", parent="1", source=u, target=v
        )
        eg = ET.SubElement(ec, "mxGeometry", attrib={"relative": "1", "as": "geometry"})
        if waypoints:
            arr = ET.SubElement(eg, "Array", attrib={"as": "points"})
            for wx, wy in waypoints:
                ET.SubElement(arr, "mxPoint", attrib={"x": str(int(wx)), "y": str(int(wy))})

    # Recompute page width/height if loop corridors expanded bounds
    all_wx = [float(pt.get("x", 0)) for pt in root.findall(".//mxPoint")]
    all_wy = [float(pt.get("y", 0)) for pt in root.findall(".//mxPoint")]
    if all_wx:
        model.set("pageWidth", str(max(int(model.get("pageWidth")), _snap(max(all_wx) + 120))))
    if all_wy:
        model.set("pageHeight", str(max(int(model.get("pageHeight")), _snap(max(all_wy) + 100))))

    tree = ET.ElementTree(mxfile)
    ET.indent(tree, space="  ")
    return tree


def main():
    ap = argparse.ArgumentParser(description="Compile a declarative JSON diagram spec into ISO 5807 .drawio XML.")
    ap.add_argument("spec", help="Path to JSON diagram specification")
    ap.add_argument("-o", "--output", required=True, help="Output .drawio path")
    ap.add_argument("--preset", default=None, help="Style preset name or path to preset .json (default: tech-warm-light)")
    ap.add_argument("--render-svg", default=None, help="Also render standalone SVG via drawio_render_svg.py")
    ap.add_argument("--render-html", default=None, help="Also render interactive HTML viewer")
    ap.add_argument("--render-runbook", default=None, help="Also export interactive step-by-step SOP Runbook HTML")
    args = ap.parse_args()

    try:
        with open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)
    except OSError as exc:
        sys.exit(f"error: cannot read spec {args.spec}: {exc}")
    except json.JSONDecodeError as exc:
        sys.exit(f"error: invalid JSON in {args.spec}: {exc}")

    try:
        tree = compile_spec_to_drawio(spec, preset_name=args.preset)
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        tree.write(args.output, encoding="utf-8", xml_declaration=False)
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        sys.exit(f"error: {exc}")

    sys.stderr.write(f"wrote {args.output}\n")

    if args.render_svg or args.render_html:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        from drawio_render_svg import render_drawio_file
        try:
            render_drawio_file(args.output, out_svg=args.render_svg, out_html=args.render_html)
        except (OSError, RuntimeError, ValueError) as exc:
            sys.exit(f"error: render failed: {exc}")

    if args.render_runbook:
        import subprocess as _sp
        r = _sp.run([sys.executable, os.path.join(HERE, "runbook.py"), args.output, "-o", args.render_runbook])
        if r.returncode != 0:
            sys.exit(r.returncode)


if __name__ == "__main__":
    main()
