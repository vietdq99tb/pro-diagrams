#!/usr/bin/env python3
"""Re-theme an EXISTING .drawio with a style preset — layout and shapes untouched.

Style presets (styles/schema.json) normally apply at generation time; this is
the post-processor for diagrams that already exist: "make this dark", "apply my
corporate style to last week's diagram".

  python3 restyle.py diagram.drawio --preset tech-warm-dark
  python3 restyle.py diagram.drawio --preset ~/.pro-diagrams/styles/corp.json -o out.drawio

What it changes, per the preset application rules in references/theme-atelier-tech-warm.md:
- Every vertex fill/stroke is remapped to the preset palette. Known built-in
  preset (fillColor, strokeColor) / fillColor values are reverse-mapped directly
  to their exact semantic slot first, preserving all 7 Atelier Technical Warm
  slots with zero collisions; unknown custom colors fall back to hue distance.
- Swimlane pool/lane headers and swimlaneFillColor body stripes are remapped
  from data/theme-tokens.json so light <-> dark conversion leaves zero harsh
  white lanes in dark mode.
- font.fontFamily on every vertex; existing fontSize values are kept (they
  encode hierarchy).
- extras: fontColor (vertices + text cells), edgeColor (edge stroke + label,
  keeping opaque labelBackgroundColor matching target canvas), sketch=1,
  globalStrokeWidth, page background on <mxGraphModel>.
Edge ROUTING styles and shape keywords are left alone — rewriting them would
break existing waypoints and geometry. fillColor=none is structural (transparent
containers, annotations) and is never given an opaque fill.

Usage: restyle.py <file.drawio> --preset <name|path.json> [-o <out.drawio>]
"""
import argparse
import colorsys
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Canonical hue (degrees) of each palette slot for unknown custom colors.
SLOT_HUES = {"primary": 210, "success": 150, "warning": 40, "accent": 12,
             "danger": 0, "secondary": 200}
SLOT_ORDER = ["primary", "success", "warning", "accent", "danger", "neutral", "secondary"]


def _hex_luminance(hex_color):
    s = str(hex_color or "").strip()
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", s):
        return 0.9
    rgb = [int(s[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _load_theme_tokens():
    tok_path = os.path.join(SKILL_DIR, "data", "theme-tokens.json")
    try:
        with open(tok_path, encoding="utf-8") as f:
            return json.load(f).get("themes", {})
    except (OSError, json.JSONDecodeError):
        return {}


def _build_builtin_slot_lookup():
    """Reverse-lookup maps from all built-in presets: (fill, stroke)->slot and fill->slot."""
    pair_map = {}
    fill_map = {}
    builtin_dir = os.path.join(SKILL_DIR, "styles", "built-in")
    if not os.path.isdir(builtin_dir):
        return pair_map, fill_map
    # Prioritize Atelier Technical Warm presets first so all 14 canonical hexes are exact
    files = sorted(f for f in os.listdir(builtin_dir) if f.endswith(".json"))
    preferred = [f for f in ("tech-warm-light.json", "tech-warm-dark.json") if f in files]
    ordered = preferred + [f for f in files if f not in preferred]
    for fname in ordered:
        try:
            with open(os.path.join(builtin_dir, fname), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        for slot, pair in (data.get("palette") or {}).items():
            if not isinstance(pair, dict):
                continue
            fc = (pair.get("fillColor") or "").lower()
            sc = (pair.get("strokeColor") or "").lower()
            if fc and sc:
                pair_map.setdefault((fc, sc), slot)
            if fc:
                fill_map.setdefault(fc, slot)
    return pair_map, fill_map


def find_preset(name):
    """Resolve a preset name/path to its JSON dict (direct path, user dir, then built-ins)."""
    candidates = [name] if (name.endswith(".json") or os.path.isfile(name)) else [
        os.path.expanduser(f"~/.pro-diagrams/styles/{name.lower()}.json"),
        os.path.join(SKILL_DIR, "styles", "built-in", f"{name.lower()}.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                sys.exit(f"error: cannot parse preset {path}: {exc}")
            if not isinstance(data, dict) or "palette" not in data or "font" not in data:
                sys.exit(f"error: invalid preset JSON structure in {path}")
            return data
    builtin = os.path.join(SKILL_DIR, "styles", "built-in")
    known = sorted(f[:-5] for f in os.listdir(builtin) if f.endswith(".json"))
    sys.exit(f"error: preset '{name}' not found (built-ins: {', '.join(known)})")


def _fallback_slot(slot, palette):
    if palette.get(slot):
        return slot
    for k in SLOT_ORDER:
        if palette.get(k):
            return k
    sys.exit("error: preset palette has no non-null slots")


def match_slot(fill_hex, stroke_hex, palette, pair_map, fill_map):
    """Exact built-in preset slot reverse-lookup first; hue-distance fallback otherwise."""
    fl = (fill_hex or "").lower()
    sl = (stroke_hex or "").lower()
    if fl and sl and (fl, sl) in pair_map:
        return _fallback_slot(pair_map[(fl, sl)], palette)
    if fl and fl in fill_map:
        return _fallback_slot(fill_map[fl], palette)
    return hue_slot(fl, palette)


def hue_slot(hexcolor, palette):
    """Nearest non-null palette slot for an existing fill color, by hue."""
    r, g, b = (int(hexcolor[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if s < 0.15 or l > 0.97 or l < 0.03:                  # grey / near-white / near-black
        slot = "neutral"
    else:
        deg = h * 360
        slot = min(SLOT_HUES, key=lambda k: min(abs(deg - SLOT_HUES[k]),
                                                360 - abs(deg - SLOT_HUES[k])))
    return _fallback_slot(slot, palette)


def get_key(style, key):
    m = re.search(rf"(?:^|;){key}=([^;]*)", style)
    return m.group(1) if m else None


def set_keys(style, **kv):
    """Replace/insert style keys, dropping existing occurrences first."""
    for key in kv:
        style = re.sub(rf"(?:^|;){key}=[^;]*", "", style)
    style = style.strip("; ")
    tail = ";".join(f"{k}={v}" for k, v in kv.items() if v is not None)
    return (style + ";" if style else "") + tail + ";"


def main():
    p = argparse.ArgumentParser(description="Apply a style preset to an existing .drawio.")
    p.add_argument("file", help="input .drawio")
    p.add_argument("--preset", required=True, help="preset name (user or built-in) or JSON path")
    p.add_argument("-o", "--output", help="output path (default: <file>-<preset>.drawio)")
    args = p.parse_args()

    if not os.path.isfile(args.file):
        sys.exit(f"error: {args.file} not found")
    preset = find_preset(args.preset)
    palette, extras, font = preset["palette"], preset.get("extras", {}), preset["font"]
    pair_map, fill_map = _build_builtin_slot_lookup()
    themes = _load_theme_tokens()

    target_bg = extras.get("background", "#F8F6F2")
    is_dark_target = _hex_luminance(target_bg) < 0.25
    target_theme = themes.get(preset.get("name")) or themes.get(
        "tech-warm-dark" if is_dark_target else "tech-warm-light", {}
    )
    target_sw = target_theme.get("swimlane", {})

    # Collect known semantic hex sets across all themes for lossless round-trips
    known_pool_fills = {t.get("swimlane", {}).get("pool_header_fill", "").lower() for t in themes.values()} - {""}
    known_lane_odd = {t.get("swimlane", {}).get("lane_body_odd", "").lower() for t in themes.values()} - {""}
    known_lane_even = {t.get("swimlane", {}).get("lane_body_even", "").lower() for t in themes.values()} - {""}
    known_crit_strokes = {t.get("edge_critical", "").lower() for t in themes.values()} - {""}
    known_danger_strokes = {
        t.get("slots", {}).get("danger", {}).get("stroke", "").lower() for t in themes.values()
    } - {""}
    known_muted = {t.get("ink_muted", "").lower() for t in themes.values()} - {""}

    target_edge_bg = target_bg
    target_edge_crit = target_theme.get("edge_critical") or (palette.get("accent") or {}).get("strokeColor")
    target_edge_danger = (palette.get("danger") or {}).get("strokeColor")
    target_ink_muted = target_theme.get("ink_muted") or extras.get("fontColor", "#526068")
    target_ink_heading = target_theme.get("ink_heading") or extras.get("fontColor", "#1C2327")

    vertex_extra = {"fontFamily": font["fontFamily"]}
    if extras.get("fontColor"):
        vertex_extra["fontColor"] = extras["fontColor"]
    if extras.get("sketch"):
        vertex_extra["sketch"] = "1"
    if extras.get("globalStrokeWidth") not in (None, 1):
        vertex_extra["strokeWidth"] = "%g" % extras["globalStrokeWidth"]

    try:
        tree = ET.parse(args.file)
    except (ET.ParseError, OSError) as exc:
        sys.exit(f"error: cannot parse {args.file}: {exc}")

    slot_map, n_vert, n_edge = {}, 0, 0
    for diagram in tree.getroot().iter("diagram"):
        model = diagram.find("mxGraphModel")
        root = model.find("root") if model is not None else None
        if root is None:
            sys.stderr.write(f"warning: skipping compressed page '{diagram.get('name', '?')}'\n")
            continue
        if extras.get("background"):
            model.set("background", extras["background"])

        all_cells = [c if c.tag == "mxCell" else c.find("mxCell") for c in root]
        all_cells = [c for c in all_cells if c is not None]
        swimlane_ids = {c.get("id") for c in all_cells if c.get("vertex") == "1" and "swimlane" in (c.get("style") or "")}
        pool_parent_ids = {
            c.get("parent") for c in all_cells
            if c.get("id") in swimlane_ids and c.get("parent") in swimlane_ids
        }
        lane_seq = 0

        for cell in all_cells:
            cid = cell.get("id") or ""
            style = cell.get("style") or ""
            if cell.get("edge") == "1":
                kv = {"fontFamily": font["fontFamily"]}
                cur_stroke = (get_key(style, "strokeColor") or "").lower()
                is_annot_edge = ("dashed=1" in style and "endArrow=none" in style)
                if is_annot_edge:
                    kv["strokeColor"] = target_ink_muted
                elif cur_stroke in known_crit_strokes and target_edge_crit:
                    kv.update(strokeColor=target_edge_crit, fontColor=target_edge_crit,
                              labelBackgroundColor=target_edge_bg)
                elif cur_stroke in known_danger_strokes and target_edge_danger:
                    kv.update(strokeColor=target_edge_danger, fontColor=target_edge_danger,
                              labelBackgroundColor=target_edge_bg)
                elif extras.get("edgeColor"):
                    kv.update(strokeColor=extras["edgeColor"], fontColor=extras["edgeColor"],
                              labelBackgroundColor=target_edge_bg)
                else:
                    kv["labelBackgroundColor"] = target_edge_bg
                if extras.get("sketch"):
                    kv["sketch"] = "1"
                if extras.get("globalStrokeWidth") not in (None, 1) and not is_annot_edge:
                    cur_sw = get_key(style, "strokeWidth")
                    if not (cur_stroke in known_crit_strokes and cur_sw):
                        kv["strokeWidth"] = "%g" % extras["globalStrokeWidth"]
                cell.set("style", set_keys(style, **kv))
                n_edge += 1
                continue

            if cell.get("vertex") != "1":
                continue

            # Swimlane Pool & Lane header + body background remapping
            if "swimlane" in style and target_sw:
                kv = {"fontFamily": font["fontFamily"]}
                cur_fill = (get_key(style, "fillColor") or "").lower()
                cur_body = (get_key(style, "swimlaneFillColor") or "").lower()
                is_pool = (cid == "pool_main") or (cid in pool_parent_ids) or (cur_fill in known_pool_fills)
                if is_pool:
                    kv.update(
                        fillColor=target_sw["pool_header_fill"],
                        fontColor=target_sw["pool_header_text"],
                        strokeColor=target_sw["pool_header_fill"],
                        swimlaneFillColor=target_theme.get("surface", target_sw["lane_body_even"]),
                    )
                else:
                    if cur_body in known_lane_odd:
                        body_fill = target_sw["lane_body_odd"]
                    elif cur_body in known_lane_even:
                        body_fill = target_sw["lane_body_even"]
                    else:
                        body_fill = target_sw["lane_body_even"] if lane_seq % 2 == 0 else target_sw["lane_body_odd"]
                    lane_seq += 1
                    kv.update(
                        fillColor=target_sw["lane_header_fill"],
                        fontColor=target_sw["lane_header_text"],
                        strokeColor=target_sw["lane_header_stroke"],
                        swimlaneFillColor=body_fill,
                    )
                cell.set("style", set_keys(style, **kv))
                n_vert += 1
                continue

            kv = dict(vertex_extra)
            fill = get_key(style, "fillColor")
            stroke = get_key(style, "strokeColor")
            if fill and re.fullmatch(r"#[0-9A-Fa-f]{6}", fill):
                slot = match_slot(fill, stroke, palette, pair_map, fill_map)
                slot_map[fill.lower()] = slot
                pair = palette[slot]
                kv.update(fillColor=pair["fillColor"], strokeColor=pair["strokeColor"])
            elif fill and fill.lower() == "none":
                if "annotation" in style.lower():
                    kv["strokeColor"] = target_ink_muted
                    kv["fontColor"] = target_ink_muted
                    kv.pop("strokeWidth", None)
                elif "text;" in style or style.startswith("text;") or cid == "title_banner":
                    kv["fontColor"] = target_ink_heading
                    kv.pop("strokeWidth", None)
                    val = cell.get("value") or ""
                    for old_m in known_muted:
                        val = re.sub(re.escape(old_m), target_ink_muted, val, flags=re.I)
                    cell.set("value", val)
            elif fill is None:
                kv.pop("fontColor", None)
            cell.set("style", set_keys(style, **kv))
            n_vert += 1

    out = args.output or "%s-%s.drawio" % (os.path.splitext(args.file)[0],
                                           preset.get("name", "restyled"))
    try:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        tree.write(out, encoding="utf-8", xml_declaration=False)
    except OSError as exc:
        sys.exit(f"error: cannot write {out}: {exc}")
    remap = ", ".join(f"{c}->{s}" for c, s in sorted(slot_map.items()))
    sys.stderr.write(f"wrote {out} ({n_vert} vertices, {n_edge} edges restyled"
                     + (f"; colors: {remap}" if remap else "") + ")\n")


if __name__ == "__main__":
    main()
