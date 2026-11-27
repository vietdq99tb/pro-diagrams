#!/usr/bin/env python3
"""Turn a flowchart / decision-tree .drawio into a click-through HTML runbook.

Parses the nodes and edges out of a .drawio and infers a node "type" from its
shape style (ellipse -> start/end, rhombus -> decision, parallelogram -> io,
else process). The ellipse with no incoming edges is taken as the start node.
The output is a single self-contained HTML page: the current node's text
front and center, one button per outgoing edge (labeled with the edge's
choice text, or "Continue" when a node has a single unlabeled successor), a
breadcrumb trail of visited nodes, Back/Restart controls, and an "end" state
on terminal nodes (no outgoing edges). No draw.io CLI is needed -- the XML is
read and the HTML is built directly, so the whole script is testable without
any external tool.

  python3 runbook.py triage.drawio -o triage.html

Usage: python3 runbook.py <file.drawio> [-o out.html]
"""
import argparse
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET


def _clean_label(raw):
    """Strip HTML tags/entities from draw.io labels while preserving explicit line breaks."""
    if not raw:
        return ""
    txt = re.sub(r"<br\s*/?>", "\n", str(raw), flags=re.I)
    txt = re.sub(r"<[^>]+>", "", txt)
    txt = html.unescape(txt)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in txt.split("\n")]
    return "\n".join(ln for ln in lines if ln).strip()


def _is_chrome_or_annotation(cid, style):
    st_l = (style or "").lower()
    cid_l = (cid or "").lower()
    if "swimlane" in st_l or "container=1" in st_l:
        return True
    if cid_l.startswith(("title", "subtitle", "header", "legend", "footer", "badge", "meta")):
        return True
    if "text;" in st_l or st_l.startswith("text;") or ("fillcolor=none" in st_l and "strokecolor=none" in st_l):
        return True
    if "mxgraph.flowchart.annotation" in st_l or "shape=note" in st_l:
        return True
    return False


def parse(path):
    """Return (nodes, edges, start_id).

    nodes: {id: {"label": str, "type": "start"|"end"|"decision"|"io"|"process", "lane"?: str}}
    edges: [{"source": id, "target": id, "label": str}, ...] in document order.
    Cells are flattened across pages; UserObject/object wrappers are unwrapped,
    HTML labels are unescaped, non-step chrome/annotations are omitted, and paired
    on-page connectors are bridged transparently.
    """
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        sys.exit(f"error: cannot parse {path}: {exc}")
    pages = tree.getroot().findall("diagram") or [tree.getroot()]
    cells, labels = [], {}
    for page in pages:
        model = page.find("mxGraphModel")
        root = model.find("root") if model is not None else None
        if root is None:
            if (page.text or "").strip():
                sys.stderr.write(f"warning: {path}: a page is compressed, skipped\n")
            continue
        for child in root:
            if child.tag == "mxCell":
                cells.append(child)
                labels[child.get("id")] = _clean_label(child.get("value") or "")
            elif child.tag in ("UserObject", "object"):
                inner = child.find("mxCell")
                if inner is not None:
                    inner.set("id", child.get("id", ""))
                    cells.append(inner)
                    labels[child.get("id")] = _clean_label(
                        child.get("label") or child.get("value") or inner.get("value") or ""
                    )

    # Collect child edgeLabel values attached to parent edges
    child_edge_labels = {}
    swimlane_names = {}
    for c in cells:
        cid = c.get("id")
        st = c.get("style") or ""
        g = c.find("mxGeometry")
        if "edgeLabel" in st or (g is not None and g.get("relative") == "1" and c.get("vertex") == "1"):
            pid = c.get("parent")
            if pid and labels.get(cid):
                child_edge_labels[pid] = labels[cid]
        elif c.get("vertex") == "1" and "swimlane" in st and cid:
            swimlane_names[cid] = labels.get(cid, "")

    parents = {c.get("parent") for c in cells}             # ids that have children
    order, styles, node_lanes, raw_edges = [], {}, {}, []
    for c in cells:
        cid = c.get("id")
        if not cid or cid in ("0", "1"):
            continue
        style = c.get("style") or ""
        if c.get("edge") == "1":
            if "dashed=1" in style and "endArrow=none" in style:
                continue
            s, t = c.get("source"), c.get("target")
            if s and t:
                elbl = labels.get(cid, "") or child_edge_labels.get(cid, "")
                raw_edges.append({"source": s, "target": t, "label": elbl})
        elif c.get("vertex") == "1" and cid not in parents:  # leaf vertices only
            if "edgeLabel" in style:
                continue
            g = c.find("mxGeometry")
            if g is not None and g.get("relative") == "1":  # edge-label child
                continue
            if _is_chrome_or_annotation(cid, style):
                continue
            order.append(cid)
            styles[cid] = style
            pid = c.get("parent")
            if pid in swimlane_names and swimlane_names[pid]:
                node_lanes[cid] = swimlane_names[pid]

    valid_ids = set(order)
    edges = [e for e in raw_edges if e["source"] in valid_ids and e["target"] in valid_ids]

    # Bridge paired on-page connectors (e.g., A(in) -> A(out)) transparently
    indeg_pre = {i: 0 for i in order}
    out_by_node = {i: [] for i in order}
    for e in edges:
        out_by_node[e["source"]].append(e)
        indeg_pre[e["target"]] += 1

    conn_by_code = {}
    for nid in order:
        if "on-page_reference" in styles[nid].lower():
            code = labels.get(nid, "").strip().upper()
            if code:
                conn_by_code.setdefault(code, []).append(nid)

    bridged_in = {}      # entry_conn_id -> list of outgoing edges from paired exit_conn
    removed_conns = set()
    for code, nids in conn_by_code.items():
        entries = [n for n in nids if indeg_pre[n] >= 1 and len(out_by_node[n]) == 0]
        exits = [n for n in nids if indeg_pre[n] == 0 and len(out_by_node[n]) >= 1]
        if entries and len(exits) == 1:
            ex_id = exits[0]
            ex_outs = out_by_node[ex_id]
            for en_id in entries:
                bridged_in[en_id] = ex_outs
                removed_conns.add(en_id)
            removed_conns.add(ex_id)

    if removed_conns:
        new_edges = []
        for e in edges:
            if e["source"] in removed_conns:
                continue
            if e["target"] in bridged_in:
                for ex_e in bridged_in[e["target"]]:
                    new_edges.append({
                        "source": e["source"],
                        "target": ex_e["target"],
                        "label": e["label"] or ex_e["label"],
                    })
            else:
                new_edges.append(e)
        edges = new_edges
        order = [nid for nid in order if nid not in removed_conns]

    indeg = {i: 0 for i in order}
    outdeg = {i: 0 for i in order}
    for e in edges:
        if e["source"] in outdeg:
            outdeg[e["source"]] += 1
        if e["target"] in indeg:
            indeg[e["target"]] += 1

    nodes = {}
    for nid in order:
        style = styles[nid]
        st_l = style.lower()
        is_term = (
            "mxgraph.flowchart.terminator" in st_l
            or ("ellipse" in st_l and "on-page_reference" not in st_l)
            or ("rounded=1" in st_l and "arcsize=50" in st_l)
        )
        if is_term:
            ntype = "end" if outdeg[nid] == 0 and indeg[nid] > 0 else "start"
        elif "rhombus" in st_l or "mxgraph.flowchart.decision" in st_l:
            ntype = "decision"
        elif "parallelogram" in st_l or "mxgraph.flowchart.data" in st_l or "manualinput" in st_l:
            ntype = "io"
        else:
            ntype = "process"
        entry = {"label": labels.get(nid, "") or nid, "type": ntype}
        if nid in node_lanes:
            entry["lane"] = node_lanes[nid]
        nodes[nid] = entry

    edges = [e for e in edges if e["source"] in nodes and e["target"] in nodes]

    # Start node: terminator/ellipse with in-degree 0; else unique in-degree-0 node; else first node
    term_zero_in = [
        nid for nid in order
        if nodes[nid]["type"] == "start" and indeg[nid] == 0
    ]
    if len(term_zero_in) == 1:
        start_id = term_zero_in[0]
    elif len(term_zero_in) > 1:
        sys.stderr.write("warning: multiple start terminator nodes with in-degree 0; picking the first\n")
        start_id = term_zero_in[0]
    else:
        zero_in = [nid for nid in order if indeg[nid] == 0]
        if len(zero_in) == 1:
            start_id = zero_in[0]
        elif len(zero_in) > 1:
            sys.stderr.write("warning: no unique in-degree-0 node; picking the first\n")
            start_id = zero_in[0]
        elif order:
            sys.stderr.write("warning: no start node found by heuristics; using the first node\n")
            start_id = order[0]
        else:
            start_id = None
    return nodes, edges, start_id


def _extract_doc_title(path):
    """Prefer the diagram's title_banner first line when available, else filename stem."""
    fallback = os.path.splitext(os.path.basename(path))[0]
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return fallback
    for cell in root.iter("mxCell"):
        if cell.get("id") == "title_banner" and cell.get("value"):
            cleaned = _clean_label(cell.get("value"))
            first_line = cleaned.split("\n", 1)[0].strip()
            if first_line:
                return first_line
    return fallback


def build_html(title, nodes, edges, start_id):
    """One self-contained click-through SOP Runbook page styled with Atelier Technical Warm."""
    adjacency = {}
    for e in edges:
        adjacency.setdefault(e["source"], []).append({"target": e["target"], "label": e["label"]})
    payload = json.dumps(
        {"nodes": nodes, "edges": adjacency, "start": start_id}, ensure_ascii=False
    ).replace("</", "<\\/")
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap">
<style>
:root{{color-scheme:light dark}}
*{{box-sizing:border-box}}
body{{margin:0;font:15px/1.55 'Open Sans','Segoe UI',Roboto,Helvetica,Arial,sans-serif;
background:#F8F6F2;color:#1C2327;min-height:100vh;display:flex;flex-direction:column;align-items:center}}
header{{width:100%;max-width:720px;padding:24px 20px 6px}}
h1{{margin:0;font-size:20px;font-weight:700;color:#2B373E}}
#crumbs{{width:100%;max-width:720px;padding:8px 20px;display:flex;flex-wrap:wrap;gap:4px;
font-size:12px;color:#526068}}
#crumbs span:not(:last-child)::after{{content:" \\2192 ";margin:0 4px;color:#526068}}
#crumbs span.prev{{text-decoration:underline;text-underline-offset:2px;cursor:pointer;color:#395E73}}
main{{width:100%;max-width:720px;padding:12px 20px 32px;flex:1}}
#card{{background:#FFFFFF;border:1px solid #C9D2D8;border-left:5px solid #2B373E;border-radius:10px;
padding:26px;box-shadow:0 2px 8px rgba(28,35,39,.06)}}
#card.start{{border-left-color:#2B373E}}
#card.decision{{border-left-color:#AD4333}}
#card.end{{border-left-color:#2D6A5B}}
#card.io{{border-left-color:#395E73}}
#card.process{{border-left-color:#4A5860}}
#type{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#526068;margin:0 0 10px}}
#label{{font-size:19px;font-weight:600;white-space:pre-wrap;color:#1C2327;margin:0 0 22px}}
.choices{{display:flex;flex-direction:column;gap:10px}}
.choices button{{font:inherit;font-weight:600;text-align:left;padding:12px 16px;border:1.5px solid #4A5860;
border-radius:8px;background:#EEF2F5;cursor:pointer;color:#1C2327;transition:background .15s,border-color .15s}}
.choices button:hover,.choices button:focus-visible{{border-color:#AD4333;background:#FDF1EE;color:#1C2327;outline:none}}
.ctl{{display:flex;gap:10px;margin-top:20px}}
.ctl button{{font:inherit;font-size:13px;font-weight:600;padding:8px 16px;border:1px solid #4A5860;border-radius:8px;
background:#FFFFFF;cursor:pointer;color:#1C2327}}
.ctl button:hover:not(:disabled),.ctl button:focus-visible{{border-color:#2B373E;background:#EEF2F5;outline:none}}
.ctl button:disabled{{opacity:.45;cursor:default}}
#endmsg{{display:none;color:#2D6A5B;font-weight:700;margin:0;padding:12px 14px;background:#EEF4F1;
border:1px solid #2D6A5B;border-radius:8px}}
@media(prefers-color-scheme:dark){{
  body{{background:#161C20;color:#F4F2EE}}
  h1{{color:#FFFFFF}}
  #crumbs,#crumbs span:not(:last-child)::after{{color:#A8B4BC}}
  #crumbs span.prev{{color:#7BA8C2}}
  #card{{background:#212A30;border-color:#384650;border-left-color:#B8C7D1;box-shadow:0 2px 10px rgba(0,0,0,.35)}}
  #card.start{{border-left-color:#B8C7D1}}
  #card.decision{{border-left-color:#E07A68}}
  #card.end{{border-left-color:#6EB5A3}}
  #card.io{{border-left-color:#7BA8C2}}
  #card.process{{border-left-color:#8D9CA6}}
  #type{{color:#A8B4BC}}
  #label{{color:#F4F2EE}}
  .choices button{{background:#26333B;border-color:#8D9CA6;color:#F4F2EE}}
  .choices button:hover,.choices button:focus-visible{{border-color:#E07A68;background:#382320;color:#F4F2EE}}
  .ctl button{{background:#212A30;border-color:#8D9CA6;color:#F4F2EE}}
  .ctl button:hover:not(:disabled),.ctl button:focus-visible{{border-color:#B8C7D1;background:#26333B}}
  #endmsg{{color:#6EB5A3;background:#1E312C;border-color:#6EB5A3}}
}}
</style></head><body>
<header><h1>{html.escape(title)}</h1></header>
<div id="crumbs" aria-label="Lộ trình đã đi"></div>
<main>
<div id="card">
<p id="type"></p>
<p id="label"></p>
<div class="choices" id="choices"></div>
<p id="endmsg">Đã hoàn tất quy trình — không còn bước tiếp theo.</p>
</div>
<div class="ctl">
  <button id="back">&larr; Quay lại</button>
  <button id="restart">&#8635; Bắt đầu lại</button>
</div>
</main>
<script>
const DATA={payload};
const TYPE_VI={{start:"Bắt đầu",end:"Kết thúc",decision:"Quyết định",io:"Dữ liệu / Nhập liệu",process:"Bước xử lý"}};
let path=[DATA.start];
const $=id=>document.getElementById(id);
function render(){{
  const cur=path[path.length-1];
  const node=DATA.nodes[cur]||{{label:String(cur),type:"process"}};
  $("card").className=node.type;
  const typeLabel=TYPE_VI[node.type]||node.type;
  $("type").textContent=node.lane?(node.lane+" · "+typeLabel):typeLabel;
  $("label").textContent=node.label;
  const choices=DATA.edges[cur]||[];
  const box=$("choices");box.innerHTML="";
  $("endmsg").style.display=choices.length?"none":"block";
  choices.forEach(c=>{{
    const b=document.createElement("button");
    const target=DATA.nodes[c.target]||{{}};
    b.textContent=c.label||(choices.length===1?"Tiếp tục →":(target.label||c.target));
    b.onclick=()=>{{path.push(c.target);render();}};
    box.appendChild(b);
  }});
  $("back").disabled=path.length<2;
  const crumbs=$("crumbs");crumbs.innerHTML="";
  path.forEach((id,i)=>{{
    const s=document.createElement("span");
    s.textContent=((DATA.nodes[id]||{{}}).label||id).replace(/\\s+/g," ");
    if(i<path.length-1){{
      s.className="prev";
      s.onclick=()=>{{path=path.slice(0,i+1);render();}};
    }}
    crumbs.appendChild(s);
  }});
}}
$("back").onclick=()=>{{if(path.length>1){{path.pop();render();}}}};
$("restart").onclick=()=>{{path=[DATA.start];render();}};
render();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description="Turn a flowchart .drawio into a click-through HTML runbook.")
    ap.add_argument("file")
    ap.add_argument("-o", "--output", help="output .html (default: alongside input)")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        sys.exit(f"error: {args.file} not found")
    nodes, edges, start_id = parse(args.file)
    if not nodes:
        sys.exit(f"error: no nodes found in {args.file}")
    if start_id is None:
        sys.exit(f"error: no start node found in {args.file}")

    title = _extract_doc_title(args.file)
    out = args.output or os.path.splitext(args.file)[0] + ".html"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(build_html(title, nodes, edges, start_id))
    except OSError as exc:
        sys.exit(f"error: cannot write {out}: {exc}")
    sys.stderr.write(f"wrote {out} ({len(nodes)} nodes, {len(edges)} edges)\n")


if __name__ == "__main__":
    main()
