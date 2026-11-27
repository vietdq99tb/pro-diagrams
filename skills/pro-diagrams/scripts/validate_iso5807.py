#!/usr/bin/env python3
"""ISO 5807:1985 semantic, geometric, and WCAG AA linter for .drawio files.

Extends `validate.py` with 12 deterministic ISO 5807:1985, Swimlane & WCAG AA
rules — each mapped to its exact ISO clause or layout/WCAG standard — and
structured `diagnostics[]` + `supportedFixes[]` output (capped to <=2 self-fix rounds).

Usage:
  python3 validate_iso5807.py diagram.drawio [--strict] [--json] [--score]
"""
import argparse
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import validate as base_val

RULE_CLAUSES = {
    "W-ISO-STYLE-STRICT": "ISO 5807:1985 §9.4.2 / §10.1.2",
    "E-ISO-CONNECTOR-PAIR": "ISO 5807:1985 §9.4.1 / §10.2.2",
    "E-ISO-START": "ISO 5807:1985 §9.4.2",
    "E-ISO-END": "ISO 5807:1985 §9.4.2",
    "E-ISO-DECISION-ENTRY": "ISO 5807:1985 §9.2.2.4",
    "W-DECISION-EXIT": "ISO 5807:1985 §9.2.2.4 / §10.3.1",
    "W-ISO-DECISION-EXIT": "ISO 5807:1985 §9.2.2.4 / §10.3.1",
    "E-ISO-DECISION-LABEL": "ISO 5807:1985 §9.2.2.4 / §10.3.1",
    "W-ISO-LOOP-PAIR": "ISO 5807:1985 §9.2.2.6",
    "W-ISO-ORPHAN": "ISO 5807:1985 §9.3.1 / §10.2.1",
    "W-ISO-FLOW-DIR": "ISO 5807:1985 §10.2.1.1 / §10.2.1.2",
    "W-ISO-SWIMLANE-CROSS": "Pro. Diagrams Swimlane Layout",
    "W-ISO-WCAG-CONTRAST": "WCAG 2.1 AA (SC 1.4.3)",
}


def _iso_diag(code, severity, subject, message, fix):
    d = base_val.diag(code, severity, subject, message, fix)
    clause = RULE_CLAUSES.get(code)
    if clause:
        d["clause"] = clause
    return d


def _clean_text(raw):
    if not raw:
        return ""
    txt = re.sub(r"<br\s*/?>", "\n", str(raw), flags=re.I)
    txt = re.sub(r"<[^>]+>", "", txt)
    return html.unescape(txt).strip()


def _style_val(style, key):
    m = re.search(rf"(?:^|;)\s*{re.escape(key)}=([^;]*)", style or "")
    return m.group(1).strip() if m else None


def _srgb_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _contrast_ratio(hex1, hex2):
    if not (re.fullmatch(r"#[0-9A-Fa-f]{6}", hex1 or "") and re.fullmatch(r"#[0-9A-Fa-f]{6}", hex2 or "")):
        return None
    def lum(h):
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        return 0.2126 * _srgb_lin(r) + 0.7152 * _srgb_lin(g) + 0.0722 * _srgb_lin(b)
    l1, l2 = lum(hex1), lum(hex2)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def _unwrap_cells(page):
    model = page.find("mxGraphModel")
    root = model.find("root") if model is not None else None
    if root is None:
        return model, []
    cells = []
    for child in root:
        if child.tag == "mxCell":
            cells.append(child)
        elif child.tag in ("UserObject", "object"):
            inner = child.find("mxCell")
            if inner is not None:
                cp = ET.Element("mxCell", dict(inner.attrib))
                cp.set("id", child.get("id", inner.get("id", "")))
                cp.set("value", child.get("label") or child.get("value") or inner.get("value", ""))
                for sub in inner:
                    cp.append(sub)
                cells.append(cp)
    return model, cells


def _is_container_or_chrome(cell, style):
    if "swimlane" in style or "container=1" in style or "group" in style:
        return True
    cid = (cell.get("id") or "").lower()
    if cid.startswith(("title", "subtitle", "header", "legend", "footer", "badge", "meta")):
        return True
    if "text;" in style or style.startswith("text;") or ("fillColor=none" in style and "strokeColor=none" in style):
        return True
    return False


def _classify_iso_symbol(style):
    st = (style or "").lower()
    if "mxgraph.flowchart.terminator" in st or ("rounded=1" in st and "arcsize=50" in st):
        return "terminator"
    if "ellipse" in st and "on-page_reference" not in st:
        return "ellipse_nonstandard"
    if "mxgraph.flowchart.decision" in st or st.startswith("rhombus") or "shape=rhombus" in st:
        return "decision"
    if "on-page_reference" in st:
        return "on_page_connector"
    if "offpageconnector" in st:
        return "off_page_connector"
    if "mxgraph.flowchart.annotation" in st or "shape=note" in st:
        return "annotation"
    if "mxgraph.flowchart.loop_limit" in st:
        return "loop_limit_end" if "flipv=1" in st else "loop_limit_start"
    if "mxgraph.flowchart.parallel_mode" in st:
        return "parallel_mode"
    return "flow_node"


def check_iso5807_page(page):
    """Run base structural checks + ISO 5807:1985 checks on one <diagram> page."""
    errors, warns = base_val.check_page(page)
    for d in errors + warns:
        if d["code"] in RULE_CLAUSES and "clause" not in d:
            d["clause"] = RULE_CLAUSES[d["code"]]

    model, cells = _unwrap_cells(page)
    if not cells:
        return errors, warns

    by_id = {c.get("id"): c for c in cells if c.get("id")}
    # Collect child edge labels attached to parent edge ids
    child_edge_labels = {}
    for c in cells:
        if base_val.is_edge_label(c):
            pid = c.get("parent")
            txt = _clean_text(c.get("value"))
            if pid and txt:
                child_edge_labels[pid] = txt

    flow_nodes = {}
    annotations = set()
    swimlanes = {}
    for c in cells:
        cid = c.get("id")
        if not cid or cid in base_val.RESERVED or c.get("vertex") != "1" or base_val.is_edge_label(c):
            continue
        st = c.get("style") or ""
        if "swimlane" in st:
            swimlanes[cid] = c
            continue
        if _is_container_or_chrome(c, st):
            continue
        kind = _classify_iso_symbol(st)
        if kind == "annotation":
            annotations.add(cid)
            continue
        flow_nodes[cid] = (c, kind, st, _clean_text(c.get("value")))

    # Edges between flow/annotation nodes
    out_edges = {nid: [] for nid in flow_nodes}
    in_edges = {nid: [] for nid in flow_nodes}
    flow_edges = []
    for c in cells:
        if c.get("edge") != "1":
            continue
        eid = c.get("id") or "?"
        src, tgt = c.get("source"), c.get("target")
        st = c.get("style") or ""
        if src in annotations or tgt in annotations or "dashed=1" in st and "endArrow=none" in st:
            continue
        lbl = _clean_text(c.get("value")) or child_edge_labels.get(eid, "")
        if src in flow_nodes and tgt in flow_nodes:
            flow_edges.append((eid, src, tgt, lbl, c, st))
            out_edges[src].append((eid, tgt, lbl, c))
            in_edges[tgt].append((eid, src, lbl, c))

    if not flow_nodes:
        return errors, warns

    # 1. W-ISO-STYLE-STRICT (ISO 5807:1985 §9.4.2 / §10.1.2): ellipse used instead of stadium terminator
    for nid, (c, kind, st, lbl) in flow_nodes.items():
        if kind == "ellipse_nonstandard":
            warns.append(_iso_diag(
                "W-ISO-STYLE-STRICT", "warning", nid,
                f"node {nid!r} ({lbl!r}) uses 'ellipse' instead of ISO 5807:1985 §9.4.2 stadium terminator",
                "replace 'ellipse;' with 'shape=mxgraph.flowchart.terminator;whiteSpace=wrap;html=1;'"
            ))

    # 2. E-ISO-CONNECTOR-PAIR (ISO 5807:1985 §9.4.1 / §10.2.2): paired entry/exit connectors per code
    conn_by_code = {}
    for nid, (c, kind, st, lbl) in flow_nodes.items():
        if kind == "on_page_connector":
            code = lbl.strip().upper() or "?"
            conn_by_code.setdefault(code, []).append(nid)
        elif kind == "off_page_connector" and not lbl.strip():
            errors.append(_iso_diag(
                "E-ISO-CONNECTOR-PAIR", "error", nid,
                f"off-page connector {nid!r} has an empty page/reference label (ISO 5807:1985 §10.2.2)",
                "set a non-empty cross-page reference label such as 'P.2 / A' on the offPageConnector"
            ))

    for code, nids in conn_by_code.items():
        sources_in = [n for n in nids if len(in_edges[n]) >= 1 and len(out_edges[n]) == 0]
        targets_out = [n for n in nids if len(out_edges[n]) >= 1 and len(in_edges[n]) == 0]
        if code == "?" or len(sources_in) < 1 or len(targets_out) != 1:
            errors.append(_iso_diag(
                "E-ISO-CONNECTOR-PAIR", "error", ",".join(nids),
                f"on-page connector code {code!r} (nodes {nids}) must have >=1 entry connector (in>0, out=0) "
                f"and exactly 1 target connector (in=0, out>0) per ISO 5807:1985 §9.4.1 / §10.2.2; "
                f"got {len(sources_in)} entry and {len(targets_out)} target",
                "pair every incoming on-page_reference(code) with a single outgoing on-page_reference(code)"
            ))

    # Build virtual connector edges so reachability traverses A(in) -> A(out)
    virtual_adj = {nid: [t for _, t, _, _ in out_edges[nid]] for nid in flow_nodes}
    virtual_rev = {nid: [s for _, s, _, _ in in_edges[nid]] for nid in flow_nodes}
    for code, nids in conn_by_code.items():
        sources_in = [n for n in nids if len(in_edges[n]) >= 1 and len(out_edges[n]) == 0]
        targets_out = [n for n in nids if len(out_edges[n]) >= 1 and len(in_edges[n]) == 0]
        if len(targets_out) == 1:
            tout = targets_out[0]
            for sin in sources_in:
                virtual_adj[sin].append(tout)
                virtual_rev[tout].append(sin)

    # 3. E-ISO-START (ISO 5807:1985 §9.4.2): >=1 start terminator (or incoming off-page connector)
    starts = [
        nid for nid, (_, kind, _, _) in flow_nodes.items()
        if kind in ("terminator", "ellipse_nonstandard", "off_page_connector")
        and len(in_edges[nid]) == 0 and len(out_edges[nid]) >= 1
    ]
    if not starts:
        errors.append(_iso_diag(
            "E-ISO-START", "error", page.get("name") or "page",
            "flowchart has no ISO 5807:1985 §9.4.2 Start Terminator (in-degree=0, out-degree>=1)",
            "add a 'shape=mxgraph.flowchart.terminator;whiteSpace=wrap;html=1;' Start node with outgoing flowline"
        ))

    # 4. E-ISO-END (ISO 5807:1985 §9.4.2): >=1 end terminator and no dead-end non-terminator nodes
    ends = [
        nid for nid, (_, kind, _, _) in flow_nodes.items()
        if kind in ("terminator", "ellipse_nonstandard", "off_page_connector")
        and len(in_edges[nid]) >= 1 and len(out_edges[nid]) == 0
    ]
    if not ends:
        errors.append(_iso_diag(
            "E-ISO-END", "error", page.get("name") or "page",
            "flowchart has no ISO 5807:1985 §9.4.2 End Terminator (in-degree>=1, out-degree=0)",
            "add a 'shape=mxgraph.flowchart.terminator;whiteSpace=wrap;html=1;' End node and connect terminal branches"
        ))

    for nid, (_, kind, _, lbl) in flow_nodes.items():
        if kind not in ("terminator", "ellipse_nonstandard", "off_page_connector", "on_page_connector"):
            if len(in_edges[nid]) >= 1 and len(out_edges[nid]) == 0:
                errors.append(_iso_diag(
                    "E-ISO-END", "error", nid,
                    f"non-terminator node {nid!r} ({lbl!r}) is a dead end (out-degree=0; ISO 5807:1985 §9.4.2)",
                    "connect this step to a downstream step, End terminator, or paired Connector"
                ))

    # 5. Decision rules (ISO 5807:1985 §9.2.2.4 & §10.3.1):
    #    - E-ISO-DECISION-ENTRY: single entrance only (in-degree <= 1)
    #    - W-ISO-DECISION-EXIT:  >3 exits harms clarity (<2 exits flagged by base W-DECISION-EXIT)
    #    - E-ISO-DECISION-LABEL: 100% of outgoing branches must carry explicit condition labels
    for nid, (_, kind, _, lbl) in flow_nodes.items():
        if kind == "decision":
            ins = in_edges[nid]
            if len(ins) > 1:
                errors.append(_iso_diag(
                    "E-ISO-DECISION-ENTRY", "error", nid,
                    f"decision {nid!r} ({lbl!r}) has {len(ins)} separate incoming flowlines "
                    f"(ISO 5807:1985 §9.2.2.4 requires a single entrance)",
                    "merge incoming flowlines on an upstream process step or on-page connector before entering the decision diamond"
                ))
            outs = out_edges[nid]
            if len(outs) > 3:
                warns.append(_iso_diag(
                    "W-ISO-DECISION-EXIT", "warning", nid,
                    f"decision {nid!r} ({lbl!r}) has {len(outs)} outgoing branches (>3 hurts ISO 5807:1985 §9.2.2.4 / §10.3.1 clarity)",
                    "split cascaded conditions into sequential binary/ternary decision diamonds"
                ))
            for eid, tgt, elbl, _ in outs:
                if not elbl.strip():
                    errors.append(_iso_diag(
                        "E-ISO-DECISION-LABEL", "error", eid,
                        f"decision branch edge {eid!r} ({nid!r} -> {tgt!r}) has no condition label (ISO 5807:1985 §9.2.2.4 / §10.3.1)",
                        "set a concise branch condition label on the edge (e.g., 'Có' / 'Không', 'Đạt' / 'Lỗi')"
                    ))

    # 6. W-ISO-LOOP-PAIR (ISO 5807:1985 §9.2.2.6): loop_limit_start and loop_limit_end count parity
    loop_starts = [nid for nid, (_, k, _, _) in flow_nodes.items() if k == "loop_limit_start"]
    loop_ends = [nid for nid, (_, k, _, _) in flow_nodes.items() if k == "loop_limit_end"]
    if len(loop_starts) != len(loop_ends):
        warns.append(_iso_diag(
            "W-ISO-LOOP-PAIR", "warning", ",".join(loop_starts + loop_ends),
            f"unbalanced ISO 5807:1985 §9.2.2.6 Loop Limit symbols: {len(loop_starts)} start vs {len(loop_ends)} end",
            "pair every 'mxgraph.flowchart.loop_limit' with a closing 'mxgraph.flowchart.loop_limit;flipV=1;'"
        ))

    # 7. W-ISO-ORPHAN (ISO 5807:1985 §9.3.1 / §10.2.1): isolated or unreachable from any Start
    reachable = set()
    stack = list(starts)
    while stack:
        cur = stack.pop()
        if cur in reachable:
            continue
        reachable.add(cur)
        for nxt in virtual_adj.get(cur, ()):
            if nxt not in reachable:
                stack.append(nxt)

    for nid, (_, kind, _, lbl) in flow_nodes.items():
        if len(virtual_adj[nid]) == 0 and len(virtual_rev[nid]) == 0:
            warns.append(_iso_diag(
                "W-ISO-ORPHAN", "warning", nid,
                f"node {nid!r} ({lbl!r}) is completely isolated (no incoming or outgoing flowlines; ISO 5807:1985 §9.3.1)",
                "connect the node into the process flow or convert it to 'mxgraph.flowchart.annotation_2'"
            ))
        elif starts and nid not in reachable:
            warns.append(_iso_diag(
                "W-ISO-ORPHAN", "warning", nid,
                f"node {nid!r} ({lbl!r}) is unreachable from any Start terminator (ISO 5807:1985 §10.2.1)",
                "add a valid incoming flowline or check connector code pairing"
            ))

    # 8. W-ISO-FLOW-DIR (ISO 5807:1985 §10.2.1.1 / §10.2.1.2): backward return edges without outer corridor waypoints
    dy_vals, dx_vals = [], []
    for eid, src, tgt, elbl, edge_cell, _ in flow_edges:
        sr = base_val.abs_rect(by_id[src], by_id)
        tr = base_val.abs_rect(by_id[tgt], by_id)
        if sr and tr:
            dy_vals.append((tr[1] + tr[3] / 2) - (sr[1] + sr[3] / 2))
            dx_vals.append((tr[0] + tr[2] / 2) - (sr[0] + sr[2] / 2))
    primary_tb = sum(abs(v) for v in dy_vals) >= sum(abs(v) for v in dx_vals)
    for eid, src, tgt, elbl, edge_cell, _ in flow_edges:
        sr = base_val.abs_rect(by_id[src], by_id)
        tr = base_val.abs_rect(by_id[tgt], by_id)
        if not (sr and tr):
            continue
        # Only flag if going strictly against dominant direction on same axis without waypoints
        wps = base_val.edge_waypoints(edge_cell)
        if primary_tb and (tr[1] + tr[3] / 2) < (sr[1] - 10) and not wps:
            warns.append(_iso_diag(
                "W-ISO-FLOW-DIR", "warning", eid,
                f"upward return edge {eid!r} ({src!r} -> {tgt!r}) has no outer-corridor waypoints (ISO 5807:1985 §10.2.1.1)",
                "route backward/retry loop edges around an outer corridor (~80px) using <Array as='points'>"
            ))
        elif (not primary_tb) and (tr[0] + tr[2] / 2) < (sr[0] - 10) and not wps:
            warns.append(_iso_diag(
                "W-ISO-FLOW-DIR", "warning", eid,
                f"leftward return edge {eid!r} ({src!r} -> {tgt!r}) has no outer-corridor waypoints (ISO 5807:1985 §10.2.1.1)",
                "route backward/retry loop edges around an outer corridor (~80px) using <Array as='points'>"
            ))

    # 9. W-ISO-SWIMLANE-CROSS (Pro. Diagrams Swimlane Layout): avoid edges running collinearly on swimlane borders
    lane_borders_x, lane_borders_y = [], []
    for lid, lc in swimlanes.items():
        lr = base_val.abs_rect(lc, by_id)
        if lr:
            lx, ly, lw, lh = lr
            lane_borders_x.extend([lx, lx + lw])
            lane_borders_y.extend([ly, ly + lh])
    for eid, src, tgt, _, edge_cell, _ in flow_edges:
        route = base_val.edge_route(edge_cell, by_id)
        if not route:
            continue
        for (x1, y1), (x2, y2) in zip(route, route[1:]):
            if abs(x1 - x2) < 1.0 and abs(y2 - y1) > 40:
                if any(abs(x1 - bx) < 4.0 for bx in lane_borders_x):
                    warns.append(_iso_diag(
                        "W-ISO-SWIMLANE-CROSS", "warning", eid,
                        f"edge {eid!r} vertical segment runs directly on top of a swimlane border (x={x1:.0f})",
                        "shift the waypoint at least 16px away from swimlane border lines"
                    ))
                    break
            if abs(y1 - y2) < 1.0 and abs(x2 - x1) > 40:
                if any(abs(y1 - by) < 4.0 for by in lane_borders_y):
                    warns.append(_iso_diag(
                        "W-ISO-SWIMLANE-CROSS", "warning", eid,
                        f"edge {eid!r} horizontal segment runs directly on top of a swimlane border (y={y1:.0f})",
                        "shift the waypoint at least 16px away from swimlane border lines"
                    ))
                    break

    # 10. W-ISO-WCAG-CONTRAST (WCAG 2.1 AA SC 1.4.3): fillColor vs fontColor contrast >= 4.5:1
    default_fg = "#1C2327"
    for nid, (c, kind, st, lbl) in flow_nodes.items():
        if not lbl:
            continue
        fill = _style_val(st, "fillColor")
        fg = _style_val(st, "fontColor") or default_fg
        if fill and fill.lower() != "none":
            ratio = _contrast_ratio(fill, fg)
            if ratio is not None and ratio < 4.5:
                warns.append(_iso_diag(
                    "W-ISO-WCAG-CONTRAST", "warning", nid,
                    f"node {nid!r} text contrast ({fg} on {fill}) is {ratio:.2f}:1 (< 4.5:1 WCAG 2.1 AA SC 1.4.3)",
                    "use a high-contrast pair from 'styles/built-in/tech-warm-light.json' or darken fontColor"
                ))

    return errors, warns


def build_structured_report(path, strict=False):
    tree = ET.parse(path)
    pages = tree.getroot().findall("diagram") or [tree.getroot()]
    all_errors, all_warns = [], []
    for page in pages:
        e, w = check_iso5807_page(page)
        all_errors.extend(e)
        all_warns.extend(w)

    findings = all_errors + all_warns
    supported_fixes = []
    seen_targets = set()
    for d in findings:
        key = (d["code"], d["subject"])
        if key not in seen_targets:
            seen_targets.add(key)
            fix_item = {
                "code": d["code"],
                "severity": d["severity"],
                "target": d["subject"],
                "action": d["fix"],
            }
            if d.get("clause"):
                fix_item["clause"] = d["clause"]
            supported_fixes.append(fix_item)

    lines = [d["message"] for d in findings]
    through = sum(1 for m in lines if "routes through" in m)
    cross = sum(1 for m in lines if " cross" in m)
    olap = sum(1 for m in lines if " overlap" in m)
    score = 20 * through + 10 * cross + 5 * olap

    compliant = (len(all_errors) == 0) and (not strict or len(all_warns) == 0)
    return {
        "file": path,
        "standard": "ISO 5807:1985",
        "iso_compliant": compliant,
        "max_self_fix_rounds": 2,
        "errors": len(all_errors),
        "warnings": len(all_warns),
        "readability_score": score,
        "score_breakdown": {"through_vertex": through, "crossings": cross, "overlaps": olap},
        "diagnostics": findings,
        "supportedFixes": supported_fixes,
    }


def run_cli(path, strict=False, as_json=False, show_score=False):
    try:
        report = build_structured_report(path, strict=strict)
    except (ET.ParseError, OSError) as exc:
        sys.stderr.write(f"error: cannot parse {path}: {exc}\n")
        return 1

    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for d in report["diagnostics"]:
            print(base_val.render(d, d["severity"]))
        status = "ISO 5807 PASS" if report["iso_compliant"] else "ISO 5807 FAIL"
        print(f"[{status}] {report['errors']} error(s), {report['warnings']} warning(s)")
        if show_score:
            sb = report["score_breakdown"]
            print(f"score: {report['readability_score']} "
                  f"({sb['through_vertex']} through-vertex, {sb['crossings']} crossings, {sb['overlaps']} overlaps)")
    return 0 if report["iso_compliant"] else 1


def main():
    ap = argparse.ArgumentParser(description="Validate a .drawio diagram against ISO 5807:1985 & WCAG AA rules.")
    ap.add_argument("file", help="Path to uncompressed .drawio file")
    ap.add_argument("--strict", action="store_true", help="Treat warnings as failure")
    ap.add_argument("--json", action="store_true", help="Emit structured diagnostics[] + supportedFixes[] JSON")
    ap.add_argument("--score", action="store_true", help="Print layout readability score")
    args = ap.parse_args()
    sys.exit(run_cli(args.file, strict=args.strict, as_json=args.json, show_score=args.score))


if __name__ == "__main__":
    main()
