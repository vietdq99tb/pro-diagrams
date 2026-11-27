#!/usr/bin/env python3
"""ISO 5807:1985 semantic, geometric, and WCAG AA linter for .drawio files.

Supports all five ISO 5807:1985 chart types (§4–§8) plus Swimlanes, multi-page
cross-page connectors (§9.4.1 / §10.2.2), per-ID Loop Limit pairing (§9.2.2.6),
explicit empty-page rejection, and clean separation of ISO 5807 compliance from
layout & contrast warnings.

Usage:
  python3 validate_iso5807.py diagram.drawio [--diagram-type auto] [--strict] [--iso-only] [--json] [--score]
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import validate as base_val

VALID_DIAGRAM_TYPES = (
    "auto",
    "data-flowchart",
    "program-flowchart",
    "system-flowchart",
    "program-network",
    "system-resources",
    "swimlane",
)

DIAGRAM_TYPE_ALIASES = {
    "iso5807-flowchart": "program-flowchart",
    "program": "program-flowchart",
    "data": "data-flowchart",
    "system": "system-flowchart",
    "network": "program-network",
    "topological-graph": "program-network",
    "resources": "system-resources",
    "cpm": "program-flowchart",
}

DATA_MEDIA_KINDS = frozenset({
    "data",
    "document",
    "multi_document",
    "database",
    "direct_data",
    "stored_data",
    "sequential_data",
    "internal_storage",
    "card",
    "paper_tape",
    "manual_input",
    "display",
})

PROCESS_KINDS = frozenset({
    "process",
    "predefined_process",
    "preparation",
    "manual_operation",
    "decision",
    "loop_limit_start",
    "loop_limit_end",
    "parallel_mode",
    "delay",
})

SPECIAL_KINDS = frozenset({
    "terminator",
    "ellipse_nonstandard",
    "on_page_connector",
    "off_page_connector",
    "ellipsis",
})

RULE_CLAUSES = {
    "E-ISO-EMPTY": "ISO 5807:1985 §4–§8",
    "W-ISO-STYLE-STRICT": "ISO 5807:1985 §9.4.2 / §10.1.2",
    "E-ISO-CONNECTOR-PAIR": "ISO 5807:1985 §9.4.1 / §10.2.2",
    "E-ISO-START": "ISO 5807:1985 §4 / §5 / §9.4.2",
    "E-ISO-END": "ISO 5807:1985 §4 / §5 / §9.4.2",
    "E-ISO-DECISION-ENTRY": "ISO 5807:1985 §9.2.2.4",
    "W-DECISION-EXIT": "ISO 5807:1985 §9.2.2.4 / §10.3.1",
    "I-LAYOUT-DECISION-FANOUT": "ISO 5807:1985 §10.3.1 (Layout Advisory)",
    "E-ISO-DECISION-LABEL": "ISO 5807:1985 §9.2.2.4 / §10.3.1",
    "E-ISO-LOOP-PAIR": "ISO 5807:1985 §9.2.2.6",
    "W-ISO-ORPHAN": "ISO 5807:1985 §9.3.1 / §10.2.1",
    "W-ISO-CONTROL-TRANSFER": "ISO 5807:1985 §9.3.2.1",
    "E-ISO-RESOURCES": "ISO 5807:1985 §8",
    "W-ISO-FLOW-DIR": "ISO 5807:1985 §10.2.1.1 / §10.2.1.2",
    "W-ISO-SWIMLANE-CROSS": "Pro. Diagrams Swimlane Layout",
    "W-ISO-WCAG-CONTRAST": "WCAG 2.1 AA (SC 1.4.3)",
}

RULE_CATEGORIES = {
    "E-ISO-EMPTY": "iso",
    "W-ISO-STYLE-STRICT": "iso",
    "E-ISO-CONNECTOR-PAIR": "iso",
    "E-ISO-START": "iso",
    "E-ISO-END": "iso",
    "E-ISO-DECISION-ENTRY": "iso",
    "W-DECISION-EXIT": "iso",
    "E-ISO-DECISION-LABEL": "iso",
    "E-ISO-LOOP-PAIR": "iso",
    "W-ISO-ORPHAN": "iso",
    "W-ISO-CONTROL-TRANSFER": "iso",
    "E-ISO-RESOURCES": "iso",
    "I-LAYOUT-DECISION-FANOUT": "layout",
    "W-ISO-FLOW-DIR": "layout",
    "W-ISO-SWIMLANE-CROSS": "layout",
    "W-ISO-WCAG-CONTRAST": "contrast",
    "W-COMPRESSED": "structure",
}

_REF_PAGE_RE = re.compile(
    r"(?:đến|tới|sang|từ|xem|to|from|see)\s+(?:trang|page|p\.?)\s*[:#]?\s*([^\s,;()\[\]]+)",
    flags=re.IGNORECASE,
)


def _normalize_diagram_type(raw):
    if not raw:
        return "auto"
    val = str(raw).strip().lower()
    val = DIAGRAM_TYPE_ALIASES.get(val, val)
    return val if val in VALID_DIAGRAM_TYPES else "program-flowchart"


def _infer_base_category(diag_dict):
    code = diag_dict.get("code", "")
    if code in RULE_CATEGORIES:
        return RULE_CATEGORIES[code]
    if code.startswith("E-"):
        return "structure"
    return "layout"


def _iso_diag(code, severity, subject, message, fix, page_name=None, category=None):
    d = base_val.diag(code, severity, subject, message, fix)
    d["category"] = category or RULE_CATEGORIES.get(code, "iso")
    clause = RULE_CLAUSES.get(code)
    if clause:
        d["clause"] = clause
    if page_name:
        d["page"] = page_name
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
    st_low = (style or "").lower()
    if "isosymbol=ellipsis" in st_low:
        return False
    if "swimlane" in st_low or "container=1" in st_low or "group" in st_low:
        return True
    cid = (cell.get("id") or "").lower()
    if cid.startswith(("title", "subtitle", "header", "legend", "footer", "badge", "meta")):
        return True
    if "text;" in st_low or st_low.startswith("text;") or ("fillcolor=none" in st_low and "strokecolor=none" in st_low):
        return True
    return False


def _classify_iso_symbol(style):
    st = (style or "").lower()
    if "isosymbol=ellipsis" in st:
        return "ellipsis"
    if "mxgraph.flowchart.terminator" in st or ("rounded=1" in st and "arcsize=50" in st):
        return "terminator"
    if "on-page_reference" in st:
        return "on_page_connector"
    if "ellipse" in st:
        return "ellipse_nonstandard"
    if "mxgraph.flowchart.decision" in st or st.startswith("rhombus") or "shape=rhombus" in st:
        return "decision"
    if "offpageconnector" in st:
        return "off_page_connector"
    if "mxgraph.flowchart.annotation" in st or "shape=note" in st:
        return "annotation"
    if "mxgraph.flowchart.loop_limit" in st:
        return "loop_limit_end" if "flipv=1" in st else "loop_limit_start"
    if "mxgraph.flowchart.parallel_mode" in st:
        return "parallel_mode"
    if "mxgraph.flowchart.delay" in st or "shape=delay" in st:
        return "delay"
    if "shape=parallelogram" in st or "mxgraph.flowchart.data" in st:
        return "data"
    if "mxgraph.flowchart.multi-document" in st or "multi-document" in st:
        return "multi_document"
    if "mxgraph.flowchart.document" in st or "shape=document" in st:
        return "document"
    if "mxgraph.flowchart.database" in st or "shape=cylinder" in st:
        return "database"
    if "mxgraph.flowchart.direct_data" in st:
        return "direct_data"
    if "mxgraph.flowchart.stored_data" in st or "shape=datastorage" in st:
        return "stored_data"
    if "mxgraph.flowchart.sequential_data" in st:
        return "sequential_data"
    if "shape=internalstorage" in st:
        return "internal_storage"
    if "shape=card" in st or "mxgraph.flowchart.card" in st:
        return "card"
    if "shape=tape" in st or "paper_tape" in st or "punched_tape" in st:
        return "paper_tape"
    if "shape=manualinput" in st:
        return "manual_input"
    if "mxgraph.flowchart.display" in st or "shape=display" in st:
        return "display"
    if "shape=trapezoid" in st:
        return "manual_operation"
    if "shape=hexagon" in st:
        return "preparation"
    if "shape=process" in st or "predefined" in st:
        return "predefined_process"
    return "process"


def _extract_ref_page(style, annot_texts):
    raw_meta = _style_val(style, "isoRefPage")
    if raw_meta:
        val = urllib.parse.unquote(raw_meta).strip()
        if val:
            return val
    for txt in annot_texts:
        m = _REF_PAGE_RE.search(txt or "")
        if m:
            ref = m.group(1).strip().rstrip(".,;:")
            if ref:
                return ref
    return None


def _is_bidirectional_edge(style):
    sa = (_style_val(style, "startArrow") or "none").lower()
    ea = (_style_val(style, "endArrow") or "block").lower()
    return sa not in ("", "none") and ea not in ("", "none")


def _extract_loop_start_id(style, lbl):
    raw_meta = _style_val(style, "isoLoopId")
    if raw_meta:
        val = urllib.parse.unquote(raw_meta).strip()
        if val:
            return val, True
    lines = [ln.strip() for ln in (lbl or "").split("\n") if ln.strip()]
    return (lines[0], False) if lines else ("", False)


def _extract_loop_end_candidates(style, lbl):
    raw_meta = _style_val(style, "isoLoopId")
    if raw_meta:
        val = urllib.parse.unquote(raw_meta).strip()
        if val:
            return [val], True
    lines = [ln.strip() for ln in (lbl or "").split("\n") if ln.strip()]
    if not lines:
        return [], False
    cands = [lines[0]]
    if lines[-1] != lines[0]:
        cands.append(lines[-1])
    return cands, False


def _parse_page_data(page, page_idx, requested_type="auto"):
    page_name = page.get("name") or f"Page {page_idx + 1}"
    errors, warns = base_val.check_page(page)
    for d in errors + warns:
        if d["code"] in RULE_CLAUSES and "clause" not in d:
            d["clause"] = RULE_CLAUSES[d["code"]]
        if "category" not in d:
            d["category"] = _infer_base_category(d)
        if "page" not in d:
            d["page"] = page_name

    model, cells = _unwrap_cells(page)
    model_dtype = model.get("isoDiagramType") if model is not None else None
    if requested_type != "auto":
        resolved_dtype = _normalize_diagram_type(requested_type)
    elif model_dtype:
        resolved_dtype = _normalize_diagram_type(model_dtype)
    else:
        resolved_dtype = "program-flowchart"

    by_id = {c.get("id"): c for c in cells if c.get("id")}
    child_edge_labels = {}
    for c in cells:
        if base_val.is_edge_label(c):
            pid = c.get("parent")
            txt = _clean_text(c.get("value"))
            if pid and txt:
                child_edge_labels[pid] = txt

    flow_nodes = {}
    annotations = {}
    swimlanes = {}
    for c in cells:
        cid = c.get("id")
        if not cid or cid in base_val.RESERVED or c.get("vertex") != "1" or base_val.is_edge_label(c):
            continue
        st = c.get("style") or ""
        if "swimlane" in st.lower():
            swimlanes[cid] = c
            continue
        if _is_container_or_chrome(c, st):
            continue
        kind = _classify_iso_symbol(st)
        if kind == "annotation":
            annotations[cid] = _clean_text(c.get("value"))
            continue
        flow_nodes[cid] = (c, kind, st, _clean_text(c.get("value")))

    out_edges = {nid: [] for nid in flow_nodes}
    in_edges = {nid: [] for nid in flow_nodes}
    bidi_neighbors = {nid: set() for nid in flow_nodes}
    flow_edges = []
    node_annot_texts = defaultdict(list)

    for c in cells:
        if c.get("edge") != "1":
            continue
        eid = c.get("id") or "?"
        src, tgt = c.get("source"), c.get("target")
        st = c.get("style") or ""
        if src in annotations and tgt in flow_nodes:
            if annotations[src]:
                node_annot_texts[tgt].append(annotations[src])
            continue
        if tgt in annotations and src in flow_nodes:
            if annotations[tgt]:
                node_annot_texts[src].append(annotations[tgt])
            continue
        if src in annotations or tgt in annotations or ("dashed=1" in st and "endArrow=none" in st and "isoLine=" not in st):
            continue
        lbl = _clean_text(c.get("value")) or child_edge_labels.get(eid, "")
        if src in flow_nodes and tgt in flow_nodes:
            is_bidi = _is_bidirectional_edge(st)
            flow_edges.append((eid, src, tgt, lbl, c, st, is_bidi))
            out_edges[src].append((eid, tgt, lbl, c, st, is_bidi))
            in_edges[tgt].append((eid, src, lbl, c, st, is_bidi))
            if is_bidi:
                bidi_neighbors[src].add(tgt)
                bidi_neighbors[tgt].add(src)

    return {
        "page": page,
        "page_idx": page_idx,
        "page_name": page_name,
        "diagram_type": resolved_dtype,
        "model": model,
        "cells": cells,
        "by_id": by_id,
        "flow_nodes": flow_nodes,
        "annotations": annotations,
        "swimlanes": swimlanes,
        "out_edges": out_edges,
        "in_edges": in_edges,
        "bidi_neighbors": bidi_neighbors,
        "flow_edges": flow_edges,
        "node_annot_texts": node_annot_texts,
        "errors": errors,
        "warns": warns,
    }


def check_iso5807_document(pages, diagram_type="auto"):
    """Validate one or more <diagram> pages together with ISO 5807:1985 §4–§11 rules.

    Returns (errors, warns, hints, resolved_diagram_type).
    """
    requested = _normalize_diagram_type(diagram_type)
    parsed = [_parse_page_data(pg, idx, requested_type=requested) for idx, pg in enumerate(pages)]
    all_errors = []
    all_warns = []
    all_hints = []

    if not parsed:
        all_errors.append(_iso_diag(
            "E-ISO-EMPTY", "error", "document",
            "diagram file contains no <diagram> pages (ISO 5807:1985 §4–§8)",
            "add at least one diagram page with valid ISO 5807 flow/data symbols",
        ))
        return all_errors, all_warns, all_hints, "program-flowchart"

    doc_dtype = parsed[0]["diagram_type"]

    # 0. Empty-page check (E-ISO-EMPTY): every page MUST contain >=1 flow/data node
    for p in parsed:
        all_errors.extend(p["errors"])
        all_warns.extend(p["warns"])
        if not p["flow_nodes"]:
            all_errors.append(_iso_diag(
                "E-ISO-EMPTY", "error", p["page_name"],
                f"page {p['page_name']!r} contains 0 ISO 5807 diagram symbols (blank or chrome-only page)",
                "add valid ISO 5807 symbols and flowlines to the page before validating",
                page_name=p["page_name"],
            ))

    non_empty_pages = [p for p in parsed if p["flow_nodes"]]
    if not non_empty_pages:
        return all_errors, all_warns, all_hints, doc_dtype

    # 1. Global Connector Pairing across ALL pages (ISO 5807:1985 §9.4.1 & §10.2.2)
    conn_records = []  # dicts: page_idx, page_name, nid, code_raw, code_norm, role, ref_page
    for p in non_empty_pages:
        p_idx = p["page_idx"]
        pname = p["page_name"]
        for nid, (c, kind, st, lbl) in p["flow_nodes"].items():
            if kind == "on_page_connector":
                code_raw = lbl.strip()
                code_norm = code_raw.casefold()
                in_deg = len(p["in_edges"][nid])
                out_deg = len(p["out_edges"][nid])
                if in_deg >= 1 and out_deg == 0:
                    role = "exit"
                elif in_deg == 0 and out_deg >= 1:
                    role = "entry"
                else:
                    role = "invalid"
                ref_page = _extract_ref_page(st, p["node_annot_texts"].get(nid, []))
                conn_records.append({
                    "page_idx": p_idx,
                    "page_name": pname,
                    "nid": nid,
                    "code_raw": code_raw or "?",
                    "code_norm": code_norm,
                    "role": role,
                    "ref_page": ref_page,
                })
            elif kind == "off_page_connector" and not lbl.strip():
                all_errors.append(_iso_diag(
                    "E-ISO-CONNECTOR-PAIR", "error", nid,
                    f"off-page connector {nid!r} on page {pname!r} has an empty reference label (ISO 5807:1985 §10.2.2)",
                    "set a non-empty cross-page reference label such as 'P.2 / A' on the offPageConnector",
                    page_name=pname,
                ))

    conn_groups = defaultdict(list)
    for rec in conn_records:
        conn_groups[rec["code_norm"]].append(rec)

    global_virtual_adj = defaultdict(list)
    global_virtual_rev = defaultdict(list)
    cross_page_exit_nodes = set()   # (page_idx, nid)
    cross_page_entry_nodes = set()  # (page_idx, nid)

    for code_norm, group in conn_groups.items():
        exits = [r for r in group if r["role"] == "exit"]
        entries = [r for r in group if r["role"] == "entry"]
        invalids = [r for r in group if r["role"] == "invalid"]
        code_disp = group[0]["code_raw"]
        desc_nodes = ", ".join(f"{r['nid']}@{r['page_name']}({r['role']})" for r in group)
        subj = ",".join(r["nid"] for r in group)
        pages_involved = sorted({r["page_name"] for r in group})

        if not code_norm or invalids or len(exits) < 1 or len(entries) != 1:
            missing_hint = []
            if not code_norm:
                missing_hint.append("connector label is empty")
            if len(exits) < 1:
                missing_hint.append(
                    f"missing outgoing/exit connector (in>0, out=0) for code {code_disp!r} "
                    f"(entry on page(s) {pages_involved})"
                )
            if len(entries) != 1:
                missing_hint.append(
                    f"expected exactly 1 resuming/entry connector (in=0, out>0) for code {code_disp!r}, "
                    f"got {len(entries)} (exit on page(s) {pages_involved})"
                )
            if invalids:
                inv_s = ", ".join(f"{r['nid']}@{r['page_name']}" for r in invalids)
                missing_hint.append(f"invalid connector degree on {inv_s}")
            all_errors.append(_iso_diag(
                "E-ISO-CONNECTOR-PAIR", "error", subj,
                f"connector code {code_disp!r} [{desc_nodes}] failed ISO 5807:1985 §9.4.1 / §10.2.2 pairing: "
                + "; ".join(missing_hint),
                "pair every exit connector (in>0, out=0) with a single matching entry connector (in=0, out>0) "
                "sharing the same code across the page or document",
                page_name=pages_involved[0] if len(pages_involved) == 1 else ",".join(pages_involved),
            ))
            continue

        entry = entries[0]
        exit_page_norms = {r["page_name"].strip().casefold() for r in exits}
        entry_page_norm = entry["page_name"].strip().casefold()

        # Verify optional cross-page annotations / isoRefPage references
        for ex in exits:
            if ex["ref_page"]:
                ref_norm = ex["ref_page"].strip().casefold()
                if ref_norm != entry_page_norm:
                    all_errors.append(_iso_diag(
                        "E-ISO-CONNECTOR-PAIR", "error", ex["nid"],
                        f"connector {code_disp!r} on page {ex['page_name']!r} references page {ex['ref_page']!r}, "
                        f"but matching entry connector is on page {entry['page_name']!r} (ISO 5807:1985 §10.2.2)",
                        f"update the cross-page reference to page {entry['page_name']!r} or move the target connector",
                        page_name=ex["page_name"],
                    ))
            if ex["page_idx"] != entry["page_idx"]:
                cross_page_exit_nodes.add((ex["page_idx"], ex["nid"]))
                cross_page_entry_nodes.add((entry["page_idx"], entry["nid"]))
            global_virtual_adj[(ex["page_idx"], ex["nid"])].append((entry["page_idx"], entry["nid"]))
            global_virtual_rev[(entry["page_idx"], entry["nid"])].append((ex["page_idx"], ex["nid"]))

        if entry["ref_page"]:
            ref_norm = entry["ref_page"].strip().casefold()
            if ref_norm not in exit_page_norms:
                actual_pages = sorted({r["page_name"] for r in exits})
                all_errors.append(_iso_diag(
                    "E-ISO-CONNECTOR-PAIR", "error", entry["nid"],
                    f"entry connector {code_disp!r} on page {entry['page_name']!r} references source page "
                    f"{entry['ref_page']!r}, but exit connector(s) are on page(s) {actual_pages} (ISO 5807:1985 §10.2.2)",
                    f"update the cross-page reference to match source page(s) {actual_pages}",
                    page_name=entry["page_name"],
                ))

    # Build global graph (within-page edges + cross-page connector bridges)
    for p in non_empty_pages:
        p_idx = p["page_idx"]
        for nid in p["flow_nodes"]:
            global_virtual_adj.setdefault((p_idx, nid), [])
            global_virtual_rev.setdefault((p_idx, nid), [])
        for eid, src, tgt, lbl, c, st, is_bidi in p["flow_edges"]:
            global_virtual_adj[(p_idx, src)].append((p_idx, tgt))
            global_virtual_rev[(p_idx, tgt)].append((p_idx, src))
            if is_bidi:
                global_virtual_adj[(p_idx, tgt)].append((p_idx, src))
                global_virtual_rev[(p_idx, src)].append((p_idx, tgt))

    # 2. Per-page & Document-level ISO 5807 checks conditioned on diagram_type (§4–§8)
    doc_starts = []
    doc_ends = []
    doc_has_process = False
    doc_has_data = False

    for p in non_empty_pages:
        p_idx = p["page_idx"]
        pname = p["page_name"]
        dtype = p["diagram_type"]
        flow_nodes = p["flow_nodes"]
        out_edges = p["out_edges"]
        in_edges = p["in_edges"]
        bidi_neighbors = p["bidi_neighbors"]
        flow_edges = p["flow_edges"]
        by_id = p["by_id"]
        swimlanes = p["swimlanes"]

        # 2a. W-ISO-STYLE-STRICT: ellipse used instead of stadium terminator
        for nid, (c, kind, st, lbl) in flow_nodes.items():
            if kind in PROCESS_KINDS:
                doc_has_process = True
            if kind in DATA_MEDIA_KINDS:
                doc_has_data = True
            if kind == "ellipse_nonstandard":
                all_warns.append(_iso_diag(
                    "W-ISO-STYLE-STRICT", "warning", nid,
                    f"node {nid!r} ({lbl!r}) uses 'ellipse' instead of ISO 5807:1985 §9.4.2 stadium terminator",
                    "replace 'ellipse;' with 'shape=mxgraph.flowchart.terminator;whiteSpace=wrap;html=1;'",
                    page_name=pname,
                ))

        # 2b. Collect Start / End nodes per diagram type
        for nid, (_, kind, _, lbl) in flow_nodes.items():
            eff_in = len(in_edges[nid]) + len(bidi_neighbors[nid])
            eff_out = len(out_edges[nid]) + len(bidi_neighbors[nid])
            raw_in = len(in_edges[nid])
            raw_out = len(out_edges[nid])

            if dtype == "data-flowchart":
                # ISO 5807 §4: begins and ends with data/document/special symbols
                if kind in (DATA_MEDIA_KINDS | {"terminator", "ellipse_nonstandard", "off_page_connector"}):
                    if raw_in == 0 and eff_out >= 1:
                        doc_starts.append((p_idx, nid))
                    if eff_in >= 1 and raw_out == 0:
                        doc_ends.append((p_idx, nid))
                elif kind == "manual_operation" and eff_in >= 1 and raw_out == 0:
                    # Physical filing/archival step in Annex A (e.g., "Lưu danh sách")
                    doc_ends.append((p_idx, nid))
                elif kind in (PROCESS_KINDS - {"manual_operation"}) and eff_in >= 1 and eff_out == 0:
                    all_errors.append(_iso_diag(
                        "E-ISO-END", "error", nid,
                        f"process node {nid!r} ({lbl!r}) in data-flowchart is a dead end with no output data symbol (ISO 5807:1985 §4)",
                        "connect this process to an output data/document/storage symbol or downstream step",
                        page_name=pname,
                    ))

            elif dtype == "system-flowchart":
                # ISO 5807 §6: control flow + data-media I/O
                if kind in ("terminator", "ellipse_nonstandard", "off_page_connector"):
                    if raw_in == 0 and raw_out >= 1:
                        doc_starts.append((p_idx, nid))
                    if raw_in >= 1 and raw_out == 0:
                        doc_ends.append((p_idx, nid))
                elif kind in DATA_MEDIA_KINDS:
                    if raw_in == 0 and eff_out >= 1:
                        # Valid data/manual input into system; record as secondary seed if no terminator start
                        pass
                    if eff_in >= 1 and raw_out == 0:
                        # Valid data/display/document output (NEVER a dead-end error!)
                        pass
                elif kind not in ("on_page_connector", "ellipsis"):
                    if eff_in >= 1 and eff_out == 0:
                        all_errors.append(_iso_diag(
                            "E-ISO-END", "error", nid,
                            f"control/process node {nid!r} ({lbl!r}) in system-flowchart is a dead end (ISO 5807:1985 §6)",
                            "connect this process to a downstream control step, End terminator, or output data symbol",
                            page_name=pname,
                        ))

            elif dtype in ("program-network", "system-resources"):
                # ISO 5807 §7 & §8: network / resource configuration — no Start/End Terminator required
                if raw_in == 0 and eff_out >= 1:
                    doc_starts.append((p_idx, nid))
                if eff_in >= 1 and raw_out == 0:
                    doc_ends.append((p_idx, nid))

            else:
                # program-flowchart (§5) & swimlane: strict Terminator start/end
                if kind in ("terminator", "ellipse_nonstandard", "off_page_connector"):
                    if raw_in == 0 and raw_out >= 1:
                        doc_starts.append((p_idx, nid))
                    if raw_in >= 1 and raw_out == 0:
                        doc_ends.append((p_idx, nid))
                elif kind not in ("on_page_connector", "ellipsis"):
                    if raw_in >= 1 and raw_out == 0:
                        all_errors.append(_iso_diag(
                            "E-ISO-END", "error", nid,
                            f"non-terminator node {nid!r} ({lbl!r}) is a dead end (out-degree=0; ISO 5807:1985 §9.4.2)",
                            "connect this step to a downstream step, End terminator, or paired Connector",
                            page_name=pname,
                        ))

        # 2c. Decision rules (ISO 5807:1985 §9.2.2.4 & §10.3.1):
        #     - E-ISO-DECISION-ENTRY: single entrance (in-degree <= 1)
        #     - E-ISO-DECISION-LABEL: 100% of exits must carry condition labels
        #     - I-LAYOUT-DECISION-FANOUT (info, category="layout"): advisory hint when >3 exits
        for nid, (_, kind, _, lbl) in flow_nodes.items():
            if kind == "decision":
                ins = in_edges[nid]
                if len(ins) > 1:
                    all_errors.append(_iso_diag(
                        "E-ISO-DECISION-ENTRY", "error", nid,
                        f"decision {nid!r} ({lbl!r}) has {len(ins)} separate incoming flowlines "
                        f"(ISO 5807:1985 §9.2.2.4 requires a single entrance)",
                        "merge incoming flowlines on an upstream process step or on-page connector before entering the decision diamond",
                        page_name=pname,
                    ))
                outs = out_edges[nid]
                if len(outs) > 3:
                    all_hints.append(_iso_diag(
                        "I-LAYOUT-DECISION-FANOUT", "info", nid,
                        f"decision {nid!r} ({lbl!r}) has {len(outs)} outgoing branches "
                        f"(valid per ISO 5807:1985 §10.3.1; consider single-stem routing 'branch_style': 'stem' "
                        f"or cascaded binary decisions for compact layout)",
                        "use single-stem branching per ISO 5807 §10.3.1(b) or split into cascaded decisions if space is tight",
                        page_name=pname,
                        category="layout",
                    ))
                for eid, tgt, elbl, _, _, _ in outs:
                    if not elbl.strip():
                        all_errors.append(_iso_diag(
                            "E-ISO-DECISION-LABEL", "error", eid,
                            f"decision branch edge {eid!r} ({nid!r} -> {tgt!r}) has no condition label (ISO 5807:1985 §9.2.2.4 / §10.3.1)",
                            "set a concise branch condition label on the edge (e.g., 'Có' / 'Không', 'Đạt' / 'Lỗi')",
                            page_name=pname,
                        ))

        # 2d. E-ISO-LOOP-PAIR (ISO 5807:1985 §9.2.2.6): per-ID matching of Loop Limit Start & End
        loop_starts = [
            (nid, st, lbl) for nid, (_, k, st, lbl) in flow_nodes.items() if k == "loop_limit_start"
        ]
        loop_ends = [
            (nid, st, lbl) for nid, (_, k, st, lbl) in flow_nodes.items() if k == "loop_limit_end"
        ]
        if loop_starts or loop_ends:
            unmatched_starts = Counter()
            start_nodes_by_id = defaultdict(list)
            for nid, st, lbl in loop_starts:
                lid, _ = _extract_loop_start_id(st, lbl)
                if not lid:
                    all_errors.append(_iso_diag(
                        "E-ISO-LOOP-PAIR", "error", nid,
                        f"loop_limit_start {nid!r} has no loop identifier (ISO 5807:1985 §9.2.2.6)",
                        "set 'loop_id' in JSON or place the loop identifier on the first line of the symbol label",
                        page_name=pname,
                    ))
                else:
                    unmatched_starts[lid] += 1
                    start_nodes_by_id[lid].append(nid)

            unmatched_ends = []
            for nid, st, lbl in loop_ends:
                cands, is_explicit = _extract_loop_end_candidates(st, lbl)
                if not cands:
                    all_errors.append(_iso_diag(
                        "E-ISO-LOOP-PAIR", "error", nid,
                        f"loop_limit_end {nid!r} has no loop identifier (ISO 5807:1985 §9.2.2.6)",
                        "set 'loop_id' in JSON or place the matching loop identifier on the first/last line of the label",
                        page_name=pname,
                    ))
                    continue
                matched_id = None
                for cand in cands:
                    if unmatched_starts.get(cand, 0) > 0:
                        matched_id = cand
                        unmatched_starts[cand] -= 1
                        break
                if matched_id is None:
                    unmatched_ends.append((nid, cands[0] if is_explicit else cands[-1]))

            remaining_starts = [(lid, cnt) for lid, cnt in unmatched_starts.items() if cnt > 0]
            if remaining_starts or unmatched_ends:
                start_desc = ", ".join(f"{lid!r} (x{cnt})" for lid, cnt in remaining_starts) or "none"
                end_desc = ", ".join(f"{nid}:{lid!r}" for nid, lid in unmatched_ends) or "none"
                bad_subj = ",".join(
                    [nid for lid, _ in remaining_starts for nid in start_nodes_by_id[lid]]
                    + [nid for nid, _ in unmatched_ends]
                )
                all_errors.append(_iso_diag(
                    "E-ISO-LOOP-PAIR", "error", bad_subj or pname,
                    f"mismatched ISO 5807:1985 §9.2.2.6 Loop Limit identifier pair(s): "
                    f"unmatched start(s)=[{start_desc}], unmatched end(s)=[{end_desc}]",
                    "ensure every loop_limit_start and loop_limit_end pair shares the exact same 'loop_id' "
                    "(or matching identifier line per §9.2.2.6)",
                    page_name=pname,
                ))

        # 2e. Control transfer label check (ISO 5807:1985 §9.3.2.1)
        for eid, src, tgt, elbl, edge_cell, st, is_bidi in flow_edges:
            if (_style_val(st, "isoLine") or "").lower() == "control_transfer" and not elbl.strip():
                all_warns.append(_iso_diag(
                    "W-ISO-CONTROL-TRANSFER", "warning", eid,
                    f"control transfer edge {eid!r} ({src!r} -> {tgt!r}) has no transfer code label "
                    f"(expected e.g. 'P', 'T', 'I' per ISO 5807:1985 §9.3.2.1)",
                    "set a concise transfer code label ('P', 'T', 'I', etc.) on the control_transfer edge",
                    page_name=pname,
                ))

        # 2f. W-ISO-FLOW-DIR (layout): backward return edges without outer corridor waypoints
        if dtype in ("program-flowchart", "swimlane", "system-flowchart"):
            dy_vals, dx_vals = [], []
            for eid, src, tgt, elbl, edge_cell, st, is_bidi in flow_edges:
                if is_bidi:
                    continue
                sr = base_val.abs_rect(by_id[src], by_id)
                tr = base_val.abs_rect(by_id[tgt], by_id)
                if sr and tr:
                    dy_vals.append((tr[1] + tr[3] / 2) - (sr[1] + sr[3] / 2))
                    dx_vals.append((tr[0] + tr[2] / 2) - (sr[0] + sr[2] / 2))
            primary_tb = sum(abs(v) for v in dy_vals) >= sum(abs(v) for v in dx_vals)
            for eid, src, tgt, elbl, edge_cell, st, is_bidi in flow_edges:
                if is_bidi:
                    continue
                if dtype == "system-flowchart":
                    # Only enforce strict flow-direction corridor on control-flow process edges
                    if flow_nodes[src][1] in DATA_MEDIA_KINDS or flow_nodes[tgt][1] in DATA_MEDIA_KINDS:
                        continue
                sr = base_val.abs_rect(by_id[src], by_id)
                tr = base_val.abs_rect(by_id[tgt], by_id)
                if not (sr and tr):
                    continue
                wps = base_val.edge_waypoints(edge_cell)
                if primary_tb and (tr[1] + tr[3] / 2) < (sr[1] - 10) and not wps:
                    all_warns.append(_iso_diag(
                        "W-ISO-FLOW-DIR", "warning", eid,
                        f"upward return edge {eid!r} ({src!r} -> {tgt!r}) has no outer-corridor waypoints (ISO 5807:1985 §10.2.1.1)",
                        "route backward/retry loop edges around an outer corridor (~80px) using <Array as='points'>",
                        page_name=pname,
                    ))
                elif (not primary_tb) and (tr[0] + tr[2] / 2) < (sr[0] - 10) and not wps:
                    all_warns.append(_iso_diag(
                        "W-ISO-FLOW-DIR", "warning", eid,
                        f"leftward return edge {eid!r} ({src!r} -> {tgt!r}) has no outer-corridor waypoints (ISO 5807:1985 §10.2.1.1)",
                        "route backward/retry loop edges around an outer corridor (~80px) using <Array as='points'>",
                        page_name=pname,
                    ))

        # 2g. W-ISO-SWIMLANE-CROSS (layout): avoid edges running collinearly on swimlane borders
        lane_borders_x, lane_borders_y = [], []
        for lid, lc in swimlanes.items():
            lr = base_val.abs_rect(lc, by_id)
            if lr:
                lx, ly, lw, lh = lr
                lane_borders_x.extend([lx, lx + lw])
                lane_borders_y.extend([ly, ly + lh])
        for eid, src, tgt, _, edge_cell, _, _ in flow_edges:
            route = base_val.edge_route(edge_cell, by_id)
            if not route:
                continue
            for (x1, y1), (x2, y2) in zip(route, route[1:]):
                if abs(x1 - x2) < 1.0 and abs(y2 - y1) > 40:
                    if any(abs(x1 - bx) < 4.0 for bx in lane_borders_x):
                        all_warns.append(_iso_diag(
                            "W-ISO-SWIMLANE-CROSS", "warning", eid,
                            f"edge {eid!r} vertical segment runs directly on top of a swimlane border (x={x1:.0f})",
                            "shift the waypoint at least 16px away from swimlane border lines",
                            page_name=pname,
                        ))
                        break
                if abs(y1 - y2) < 1.0 and abs(x2 - x1) > 40:
                    if any(abs(y1 - by) < 4.0 for by in lane_borders_y):
                        all_warns.append(_iso_diag(
                            "W-ISO-SWIMLANE-CROSS", "warning", eid,
                            f"edge {eid!r} horizontal segment runs directly on top of a swimlane border (y={y1:.0f})",
                            "shift the waypoint at least 16px away from swimlane border lines",
                            page_name=pname,
                        ))
                        break

        # 2h. W-ISO-WCAG-CONTRAST (contrast): fillColor vs fontColor contrast >= 4.5:1
        default_fg = "#1C2327"
        for nid, (c, kind, st, lbl) in flow_nodes.items():
            if not lbl or kind == "ellipsis":
                continue
            fill = _style_val(st, "fillColor")
            fg = _style_val(st, "fontColor") or default_fg
            if fill and fill.lower() != "none":
                ratio = _contrast_ratio(fill, fg)
                if ratio is not None and ratio < 4.5:
                    all_warns.append(_iso_diag(
                        "W-ISO-WCAG-CONTRAST", "warning", nid,
                        f"node {nid!r} text contrast ({fg} on {fill}) is {ratio:.2f}:1 (< 4.5:1 WCAG 2.1 AA SC 1.4.3)",
                        "use a high-contrast pair from 'styles/built-in/tech-warm-light.json' or darken fontColor",
                        page_name=pname,
                    ))

    # 3. Document-level Start / End & Resource Configuration checks by chart type
    first_pname = non_empty_pages[0]["page_name"]
    if doc_dtype in ("program-flowchart", "swimlane"):
        if not doc_starts:
            all_errors.append(_iso_diag(
                "E-ISO-START", "error", first_pname,
                "flowchart has no ISO 5807:1985 §9.4.2 Start Terminator (in-degree=0, out-degree>=1)",
                "add a 'shape=mxgraph.flowchart.terminator;whiteSpace=wrap;html=1;' Start node with outgoing flowline",
                page_name=first_pname,
            ))
        if not doc_ends:
            all_errors.append(_iso_diag(
                "E-ISO-END", "error", first_pname,
                "flowchart has no ISO 5807:1985 §9.4.2 End Terminator (in-degree>=1, out-degree=0)",
                "add a 'shape=mxgraph.flowchart.terminator;whiteSpace=wrap;html=1;' End node and connect terminal branches",
                page_name=first_pname,
            ))
    elif doc_dtype == "data-flowchart":
        if not doc_starts:
            all_errors.append(_iso_diag(
                "E-ISO-START", "error", first_pname,
                "data-flowchart has no starting data/document symbol (in-degree=0, out-degree>=1; ISO 5807:1985 §4)",
                "begin the data-flowchart with a data, document, multi_document, or input medium symbol",
                page_name=first_pname,
            ))
        if not doc_ends:
            all_errors.append(_iso_diag(
                "E-ISO-END", "error", first_pname,
                "data-flowchart has no ending data/document symbol (in-degree>=1, out-degree=0; ISO 5807:1985 §4)",
                "terminate the data-flowchart with an output document, multi_document, storage, or filing symbol",
                page_name=first_pname,
            ))
    elif doc_dtype == "system-flowchart":
        # System flowchart allows Terminator starts/ends OR data-media entry/exit backbone
        data_starts = [
            (p["page_idx"], nid)
            for p in non_empty_pages
            for nid, (_, kind, _, _) in p["flow_nodes"].items()
            if kind in DATA_MEDIA_KINDS and len(p["in_edges"][nid]) == 0 and (len(p["out_edges"][nid]) + len(p["bidi_neighbors"][nid])) >= 1
        ]
        data_ends = [
            (p["page_idx"], nid)
            for p in non_empty_pages
            for nid, (_, kind, _, _) in p["flow_nodes"].items()
            if kind in DATA_MEDIA_KINDS and (len(p["in_edges"][nid]) + len(p["bidi_neighbors"][nid])) >= 1 and len(p["out_edges"][nid]) == 0
        ]
        if not doc_starts and not data_starts:
            all_errors.append(_iso_diag(
                "E-ISO-START", "error", first_pname,
                "system-flowchart has neither a Start Terminator nor any input data/manual_input symbol (ISO 5807:1985 §6)",
                "add a Start Terminator or input data/manual_input symbol feeding into the first process",
                page_name=first_pname,
            ))
        if not doc_ends and not data_ends:
            all_errors.append(_iso_diag(
                "E-ISO-END", "error", first_pname,
                "system-flowchart has neither an End Terminator nor any output display/document/data symbol (ISO 5807:1985 §6)",
                "add an End Terminator or output display/document/data symbol at the end of the system flow",
                page_name=first_pname,
            ))
    elif doc_dtype == "system-resources":
        if not (doc_has_process and doc_has_data):
            all_errors.append(_iso_diag(
                "E-ISO-RESOURCES", "error", first_pname,
                "system-resources chart must show both processing unit(s) and data/storage unit(s) (ISO 5807:1985 §8)",
                "include at least one process/manual_operation unit connected to data/storage/device symbols",
                page_name=first_pname,
            ))
    elif doc_dtype == "program-network":
        if not doc_has_process:
            all_errors.append(_iso_diag(
                "E-ISO-START", "error", first_pname,
                "program-network chart has no program/process units (ISO 5807:1985 §7)",
                "add connected program/process nodes and data interactions",
                page_name=first_pname,
            ))

    # 4. Global Reachability & Orphan Detection (W-ISO-ORPHAN)
    reachable = set()
    seed_nodes = list(doc_starts)
    if doc_dtype == "system-flowchart" and not seed_nodes:
        seed_nodes = [
            (p["page_idx"], nid)
            for p in non_empty_pages
            for nid, (_, kind, _, _) in p["flow_nodes"].items()
            if kind in DATA_MEDIA_KINDS and len(p["in_edges"][nid]) == 0 and len(p["out_edges"][nid]) >= 1
        ]
    stack = list(seed_nodes)
    while stack:
        cur = stack.pop()
        if cur in reachable:
            continue
        reachable.add(cur)
        for nxt in global_virtual_adj.get(cur, ()):
            if nxt not in reachable:
                stack.append(nxt)

    for p in non_empty_pages:
        p_idx = p["page_idx"]
        pname = p["page_name"]
        dtype = p["diagram_type"]
        for nid, (_, kind, _, lbl) in p["flow_nodes"].items():
            key = (p_idx, nid)
            deg_out = len(global_virtual_adj.get(key, ()))
            deg_in = len(global_virtual_rev.get(key, ()))
            if deg_out == 0 and deg_in == 0:
                all_warns.append(_iso_diag(
                    "W-ISO-ORPHAN", "warning", nid,
                    f"node {nid!r} ({lbl!r}) is completely isolated (no incoming or outgoing flowlines; ISO 5807:1985 §9.3.1)",
                    "connect the node into the flow or convert it to 'mxgraph.flowchart.annotation_2'",
                    page_name=pname,
                ))
            elif dtype in ("program-flowchart", "swimlane", "data-flowchart") and seed_nodes and key not in reachable:
                all_warns.append(_iso_diag(
                    "W-ISO-ORPHAN", "warning", nid,
                    f"node {nid!r} ({lbl!r}) is unreachable from any Start node (ISO 5807:1985 §10.2.1)",
                    "add a valid incoming flowline or check connector code pairing",
                    page_name=pname,
                ))
            elif dtype == "system-flowchart" and seed_nodes and key not in reachable:
                # In ISO §6 system flowcharts, data/media inputs feeding a reachable process are valid inputs!
                feeds_reachable = (
                    kind in DATA_MEDIA_KINDS
                    and any(nxt in reachable for nxt in global_virtual_adj.get(key, ()))
                )
                if not feeds_reachable:
                    all_warns.append(_iso_diag(
                        "W-ISO-ORPHAN", "warning", nid,
                        f"node {nid!r} ({lbl!r}) is unreachable in system-flowchart (ISO 5807:1985 §6 / §10.2.1)",
                        "connect this node to the active control backbone or to a reachable process",
                        page_name=pname,
                    ))

    return all_errors, all_warns, all_hints, doc_dtype


def check_iso5807_page(page, diagram_type="auto"):
    """Backwards-compatible single-page validator returning (errors, warnings)."""
    errors, warns, _hints, _dtype = check_iso5807_document([page], diagram_type=diagram_type)
    return errors, warns


def build_structured_report(path, strict=False, diagram_type="auto", iso_only=False):
    tree = ET.parse(path)
    pages = tree.getroot().findall("diagram")
    if not pages:
        # Handle bare <mxGraphModel> root or empty <mxfile/> cleanly
        root_el = tree.getroot()
        pages = [root_el] if root_el.find("mxGraphModel") is not None else []

    all_errors, all_warns, all_hints, resolved_dtype = check_iso5807_document(
        pages, diagram_type=diagram_type
    )

    findings = all_errors + all_warns + all_hints
    supported_fixes = []
    seen_targets = set()
    for d in all_errors + all_warns:
        key = (d["code"], d["subject"], d.get("page", ""))
        if key not in seen_targets:
            seen_targets.add(key)
            fix_item = {
                "code": d["code"],
                "severity": d["severity"],
                "category": d.get("category", "iso"),
                "target": d["subject"],
                "action": d["fix"],
            }
            if d.get("clause"):
                fix_item["clause"] = d["clause"]
            if d.get("page"):
                fix_item["page"] = d["page"]
            supported_fixes.append(fix_item)

    lines = [d["message"] for d in findings]
    through = sum(1 for m in lines if "routes through" in m)
    cross = sum(1 for m in lines if " cross" in m)
    olap = sum(1 for m in lines if " overlap" in m)
    score = 20 * through + 10 * cross + 5 * olap

    iso_errors = sum(1 for d in all_errors if d.get("category") == "iso")
    structure_errors = sum(1 for d in all_errors if d.get("category") == "structure")
    iso_warnings = sum(1 for d in all_warns if d.get("category") == "iso")
    layout_warnings = sum(1 for d in all_warns if d.get("category") == "layout")
    contrast_warnings = sum(1 for d in all_warns if d.get("category") == "contrast")

    # Separate ISO 5807 compliance from layout & contrast warnings
    iso_compliant = (len(all_errors) == 0) and (not strict or iso_warnings == 0)
    layout_clean = (layout_warnings == 0)
    contrast_clean = (contrast_warnings == 0)
    if iso_only:
        passed = iso_compliant
    else:
        passed = (len(all_errors) == 0) and (not strict or len(all_warns) == 0)

    return {
        "file": path,
        "standard": "ISO 5807:1985",
        "diagram_type": resolved_dtype,
        "iso_compliant": iso_compliant,
        "layout_clean": layout_clean,
        "contrast_clean": contrast_clean,
        "passed": passed,
        "max_self_fix_rounds": 2,
        "errors": len(all_errors),
        "warnings": len(all_warns),
        "hints": len(all_hints),
        "summary": {
            "iso_errors": iso_errors,
            "structure_errors": structure_errors,
            "iso_warnings": iso_warnings,
            "layout_warnings": layout_warnings,
            "contrast_warnings": contrast_warnings,
            "hints": len(all_hints),
        },
        "readability_score": score,
        "score_breakdown": {"through_vertex": through, "crossings": cross, "overlaps": olap},
        "diagnostics": findings,
        "supportedFixes": supported_fixes,
    }


def run_cli(path, strict=False, as_json=False, show_score=False, diagram_type="auto", iso_only=False):
    try:
        report = build_structured_report(
            path, strict=strict, diagram_type=diagram_type, iso_only=iso_only
        )
    except (ET.ParseError, OSError) as exc:
        sys.stderr.write(f"error: cannot parse {path}: {exc}\n")
        return 1

    if as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for d in report["diagnostics"]:
            print(base_val.render(d, d["severity"]))
        if report["passed"]:
            status = "ISO 5807 PASS"
        elif report["iso_compliant"]:
            status = "ISO 5807 PASS (LAYOUT/CONTRAST WARN)"
        else:
            status = "ISO 5807 FAIL"
        hint_part = f", {report['hints']} hint(s)" if report["hints"] else ""
        print(
            f"[{status}] ({report['diagram_type']}) "
            f"{report['errors']} error(s), {report['warnings']} warning(s){hint_part}"
        )
        if show_score:
            sb = report["score_breakdown"]
            print(
                f"score: {report['readability_score']} "
                f"({sb['through_vertex']} through-vertex, {sb['crossings']} crossings, {sb['overlaps']} overlaps)"
            )
    return 0 if report["passed"] else 1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(
        description="Validate a .drawio diagram against ISO 5807:1985 (§4–§11) & WCAG AA rules."
    )
    ap.add_argument("file", help="Path to uncompressed .drawio file")
    ap.add_argument(
        "--diagram-type", default="auto", choices=VALID_DIAGRAM_TYPES,
        help="ISO 5807:1985 diagram type (§4–§8) or 'auto' to read isoDiagramType from XML"
    )
    ap.add_argument("--strict", action="store_true", help="Treat warnings as failure (info hints never fail)")
    ap.add_argument(
        "--iso-only", action="store_true",
        help="Gate pass/fail purely on ISO 5807 + structural rules (ignore layout/contrast warnings)"
    )
    ap.add_argument("--json", action="store_true", help="Emit structured diagnostics[] + supportedFixes[] JSON")
    ap.add_argument("--score", action="store_true", help="Print layout readability score")
    args = ap.parse_args()
    sys.exit(run_cli(
        args.file,
        strict=args.strict,
        as_json=args.json,
        show_score=args.score,
        diagram_type=args.diagram_type,
        iso_only=args.iso_only,
    ))


if __name__ == "__main__":
    main()
