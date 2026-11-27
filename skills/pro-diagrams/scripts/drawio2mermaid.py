#!/usr/bin/env python3
"""Convert a .drawio into Mermaid flowchart text (diagrams-as-code).

The other reverse tool, `explain.py`, turns a diagram into prose; this turns it
into a **Mermaid `flowchart`** you can paste into a Markdown file and have
GitHub / GitLab / docs render natively — handy when you want the diagram to live
as maintainable text next to the code. Containers become `subgraph`s, edge
labels are kept, and a few shapes map to Mermaid node forms (cylinder → database
`[( )]`, rhombus → decision `{ }`, else `[ ]`).

  python3 drawio2mermaid.py architecture.drawio            # Mermaid to stdout
  python3 drawio2mermaid.py c4.drawio --fenced -o out.md   # ```mermaid fenced

Multi-page files emit one flowchart per page. This is a structural conversion —
styling, colours and vendor icons do not survive (Mermaid has no equivalent);
for a faithful, richly-styled diagram keep the `.drawio`.

Usage: python3 drawio2mermaid.py <file.drawio> [-o out] [--direction TD|LR] [--fenced]
"""
import argparse
import html
import re
import sys
import xml.etree.ElementTree as ET


def clean(text):
    """Strip the HTML draw.io stores in labels; keep line breaks as <br/>."""
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"[ \t]+", " ", text).strip()


def esc(label):
    """Mermaid-safe quoted label: escape quotes, newlines -> <br/>."""
    label = label.replace('"', "&quot;").replace("\n", "<br/>")
    return label or " "


def node_form(safe_id, label, style):
    """Mermaid node declaration, shape chosen from the draw.io style."""
    lbl = f'"{esc(label)}"'
    if any(k in style for k in ("shape=cylinder", "shape=datastore", "mxgraph.flowchart.database", "direct_data")):
        return f"{safe_id}[({lbl})]"                    # database
    if "rhombus" in style or "mxgraph.flowchart.decision" in style:
        return f"{safe_id}{{{lbl}}}"                    # decision
    if "mxgraph.flowchart.terminator" in style or ("rounded=1" in style and "arcSize=50" in style):
        return f"{safe_id}([{lbl}])"                    # stadium terminator
    if "parallelogram" in style or "mxgraph.flowchart.data" in style:
        return f"{safe_id}[/{lbl}/]"                    # data I/O
    if "shape=process" in style or "predefined_process" in style:
        return f"{safe_id}[[{lbl}]]"                    # subroutine
    if "shape=hexagon" in style:
        return f"{safe_id}{{{{{lbl}}}}}"                # preparation hexagon
    if "ellipse" in style or "shape=cloud" in style or "on-page_reference" in style:
        return f"{safe_id}(({lbl}))"                    # circle / connector
    return f"{safe_id}[{lbl}]"                          # default box


def cells_of(page):
    """(cell, id, label) for a page, unwrapping UserObject/object wrappers."""
    model = page.find("mxGraphModel")
    root = model.find("root") if model is not None else None
    if root is None:
        return None
    out = []
    for child in root:
        if child.tag == "mxCell":
            out.append((child, child.get("id"), clean(child.get("value"))))
        elif child.tag in ("UserObject", "object"):
            inner = child.find("mxCell")
            if inner is not None:
                inner.set("id", child.get("id", ""))
                out.append((inner, child.get("id"),
                            clean(child.get("label") or child.get("value"))))
    return out


def _is_chrome_or_annotation(cid, style):
    st_l = (style or "").lower()
    cid_l = (cid or "").lower()
    if cid_l.startswith(("title", "subtitle", "header", "legend", "footer", "badge", "meta")):
        return True
    if "text;" in st_l or st_l.startswith("text;") or ("fillcolor=none" in st_l and "strokecolor=none" in st_l):
        return True
    if "mxgraph.flowchart.annotation" in st_l or "shape=note" in st_l:
        return True
    return False


def page_to_mermaid(page, direction):
    cells = cells_of(page)
    if cells is None:
        return "%% (compressed page — skipped)"
    label = {cid: lbl for _, cid, lbl in cells}
    style = {cid: (c.get("style") or "") for c, cid, _ in cells}
    parents = {c.get("parent") for c, _, _ in cells if c.get("parent")}

    verts = [(c, cid) for c, cid, _ in cells if c.get("vertex") == "1"]
    containers = {cid for c, cid in verts if cid in parents}
    leaves = [(c, cid) for c, cid in verts
              if cid not in containers
              and "edgeLabel" not in style.get(cid, "")
              and not _is_chrome_or_annotation(cid, style.get(cid, ""))]

    sid = {cid: f"n{i}" for i, (_, cid) in enumerate(leaves)}   # mermaid-safe ids
    lines = [f"flowchart {direction}"]

    # Nodes, grouped into subgraphs by their container.
    by_container = {}
    for c, cid in leaves:
        parent = c.get("parent")
        key = parent if parent in containers else None
        by_container.setdefault(key, []).append(cid)

    def emit_node(cid, indent):
        lines.append(indent + node_form(sid[cid], label.get(cid) or cid, style.get(cid, "")))

    for cid in by_container.get(None, []):
        emit_node(cid, "    ")
    for cont, members in by_container.items():
        if cont is None:
            continue
        lines.append(f'    subgraph {sid.get(cont, "g_" + cont)}["{esc(label.get(cont) or "")}"]')
        for cid in members:
            emit_node(cid, "        ")
        lines.append("    end")

    # Edges (only between leaves we emitted).
    for c, _, _ in cells:
        if c.get("edge") != "1":
            continue
        est = c.get("style") or ""
        if "dashed=1" in est and "endArrow=none" in est:
            continue
        s, t = c.get("source"), c.get("target")
        if s in sid and t in sid:
            lbl = clean(c.get("value"))
            arrow = f'-->|"{esc(lbl)}"|' if lbl else "-->"
            lines.append(f"    {sid[s]} {arrow} {sid[t]}")
    return "\n".join(lines)


def main():
    import os
    ap = argparse.ArgumentParser(description="Convert a .drawio to Mermaid flowchart text.")
    ap.add_argument("file")
    ap.add_argument("-o", "--output", help="output path (default: stdout)")
    ap.add_argument("--direction", default="TD", choices=["TD", "LR", "TB", "RL", "BT"])
    ap.add_argument("--fenced", action="store_true", help="wrap each graph in a ```mermaid fence")
    args = ap.parse_args()
    try:
        root = ET.parse(args.file).getroot()
    except (ET.ParseError, OSError) as exc:
        sys.exit(f"error: cannot parse {args.file}: {exc}")
    pages = root.findall("diagram") or [root]

    blocks = []
    for i, page in enumerate(pages, 1):
        graph = page_to_mermaid(page, args.direction)
        name = page.get("name")
        if len(pages) > 1 and name:
            graph = f"%% Page {i}: {name}\n{graph}"
        blocks.append(f"```mermaid\n{graph}\n```" if args.fenced else graph)

    text = ("\n\n".join(blocks)).rstrip() + "\n"
    if args.output:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError as exc:
            sys.exit(f"error: cannot write {args.output}: {exc}")
        sys.stderr.write(f"wrote {args.output} ({len(pages)} page{'s' if len(pages) != 1 else ''})\n")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
