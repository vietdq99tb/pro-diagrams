# Shape index attribution

`shape-index.json.gz` is a gzipped copy of the shape search index from
[jgraph/drawio-mcp](https://github.com/jgraph/drawio-mcp) (`shape-search/search-index.json`),
which is generated from the official draw.io / diagrams.net client shape
libraries. Both upstream sources are licensed under the **Apache License 2.0**.

Per **Apache License 2.0 Section 4(a)**, the full verbatim license text is bundled
alongside this index at [`APACHE-2.0.txt`](./APACHE-2.0.txt).

- Each entry is `{style, w, h, title, tags, type}` for one palette shape.
- 10,446 shapes spanning AWS, Azure, GCP, Cisco, Kubernetes, UML, BPMN, P&ID,
  electrical, flowchart, network, and the general shape sets.
- Used read-only by `scripts/shapesearch.py` to resolve exact official style
  strings instead of hand-guessing them.

To refresh against a newer draw.io release, regenerate upstream with
`shape-search/generate-index.js` in the drawio-mcp repo, then re-gzip:

    gzip -9 -c search-index.json > data/shape-index.json.gz
