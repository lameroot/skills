"""bundle-visualize: generate a self-contained interactive OKF graph (Cytoscape.js + marked)."""
from __future__ import annotations

import argparse
import json as _json
from pathlib import Path

from envelope import emit_error, emit_success
from indexer import open_db, walk_concepts as _walk
from registry import register
from vault import resolve_vault

_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OKF Bundle – {name}</title>
<script src="https://unpkg.com/cytoscape@3/dist/cytoscape.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:system-ui;display:flex;height:100vh}}
#cy{{flex:1;height:100%}}#panel{{width:380px;overflow-y:auto;padding:16px;background:#f8f9fa;border-left:1px solid #ddd}}
#panel h2{{margin-bottom:4px}}#panel .meta{{font-size:13px;color:#555;margin-bottom:12px}}
#panel .body{{line-height:1.6}}#search{{width:100%;padding:8px;margin-bottom:16px;border:1px solid #ccc;border-radius:4px}}
.filter-row{{display:flex;gap:8px;margin-bottom:16px}}#type-filter{{flex:1;padding:8px;border:1px solid #ccc;border-radius:4px}}
.tag{{display:inline-block;background:#e9ecef;padding:2px 8px;border-radius:8px;font-size:12px;margin:2px}}
.concept-link{{color:#2563eb;cursor:pointer}}
</style></head><body><div id="cy"></div><div id="panel">
<input id="search" placeholder="Search concepts...">
<div class="filter-row">
<select id="type-filter"><option value="">All types</option></select>
<select id="layout-select"><option value="cose">Force-directed</option><option value="breadthfirst">Breadth-first</option><option value="concentric">Concentric</option></select>
</div><div id="detail"></div></div>
<script>
const bundle = {data};
const nodes = bundle.concepts.map(c => ({{ data: {{ id: c.id, label: c.title || c.id, type: c.type, body: c.body, description: c.description, tags: c.tags || [], links: c.links || [], resource: c.resource }}}})).concat(
  bundle.concepts.flatMap(c => (c.links||[]).map(t => ({{data:{{id:c.id+'_'+t,source:c.id,target:t}}}})))
);
const types = [...new Set(bundle.concepts.map(c=>c.type))];
types.forEach(t=>{{const o=document.createElement('option');o.value=t;o.textContent=t;document.getElementById('type-filter').appendChild(o)}});
const cy = cytoscape({{container:document.getElementById('cy'),elements:nodes,style:[
{{selector:'node',style:{{label:'data(label)',width:18,height:18,'background-color':'#3b82f6','font-size':10,'text-valign':'bottom','text-halign':'center','text-wrap':'ellipsis','text-max-width':'120px','text-overflow-wrap':'anywhere'}}}},
{{selector:'edge',style:{{width:1,'line-color':'#ccc','target-arrow-shape':'triangle','target-arrow-color':'#ccc','curve-style':'bezier'}}}},
{{selector:'.highlighted',style:{{width:24,height:24,'border-width':3}}}},
],layout:{{name:'cose'}}}});
cy.on('tap','node',e=>{{const d=e.target.data();document.getElementById('detail').innerHTML='<h2>'+d.label+'</h2><div class=meta>'+d.type+' · tags: '+(d.tags||[]).map(t=>'<span class=tag>'+t+'</span>').join(' ')+(d.resource?' · <a href='+d.resource+' target=_blank>source</a>':'')+'</div><div class=body>'+marked.parse(d.body||d.description||'')+'</div><div><strong>Links:</strong> '+(d.links||[]).map(l=>'<span class=concept-link>'+l+'</span>').join(', ')+'</div>'}});
document.getElementById('search').addEventListener('input',e=>{{const q=e.target.value.toLowerCase();cy.nodes().forEach(n=>{{const d=n.data();n.style('display',(d.label||'').toLowerCase().includes(q)||(d.body||'').toLowerCase().includes(q)?'element':'none')}})}});
document.getElementById('type-filter').addEventListener('change',e=>{{const t=e.target.value;cy.nodes().forEach(n=>n.style('display',!t||n.data().type===t?'element':'none'))}});
document.getElementById('layout-select').addEventListener('change',e=>cy.layout({{name:e.target.value}}).run());
</script></body></html>"""


def _collect_bundle(vault: Path) -> dict:
    concepts = []
    link_index = {}  # slug -> concept id
    # first pass: collect concepts
    for rel, meta, body, _mtime in _walk(vault):
        cid = str(rel)
        title = meta.get("title", "")
        tags = meta.get("tags") or []
        links_raw = _extract_links(body)
        concepts.append({"id": cid, "title": title, "type": meta.get("type", ""), "description": meta.get("description", ""), "body": body, "tags": tags, "links": links_raw, "resource": meta.get("resource", "")})
        slug = rel.replace(".md", "")
        link_index[slug] = cid
    # second pass: resolve relative links to concept ids
    for c in concepts:
        resolved = []
        for target in c.get("links", []):
            norm = target.replace(".md", "").lstrip("/")
            if norm in link_index:
                resolved.append(link_index[norm])
        c["links"] = resolved
    return {"concepts": concepts}


def _extract_links(body: str) -> list[str]:
    import re
    return re.findall(r"\]\((/[^)]+)\)", body or "")


@register("bundle", "visualize")
def bundle_visualize(args: argparse.Namespace, out, err) -> int:
    vault = resolve_vault(create=False)
    data = _collect_bundle(vault)
    name = Path(str(vault)).name
    html = _HTML.replace("{data}", _json.dumps(data, ensure_ascii=False)).replace("{name}", name)
    dest = Path(getattr(args, "out", f"{vault}/viz.html") or f"{vault}/viz.html")
    dest.write_text(html, encoding="utf-8")
    emit_success({"saved": str(dest), "concepts": len(data["concepts"])}, out)
    return 0
