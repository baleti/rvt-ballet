# Hidden line 3D style (web/hl.js)

Revit's hidden-line look is the default 3D style of rvt-viewer; Shaded, Consistent Colors, Realistic and Wireframe are switchable (header select `#vsSel`, `window.vstyle`, `?style=`/`?vs=`).

## How it works
* **Faces**: the patched mesh shader of `web/app.js` (uniform `uStyle`) outputs the element's override colour, unlit (white by default), with `polygonOffset` so edges win the depth test. Per element colour / opacity come from a data texture (`tOvr`).
* **Translucent elements** (view transparency, e.g. Floors 15 %): drawn in a second pass by a twin mesh; their faces do not write depth, so lines behind them show faint, as in Revit.
* **Edges**: a worker extracts them once per mesh (cached in IndexedDB, `rvt-hl-edges`): vertices welded within 1 mm; an edge is kept when it is a boundary / non-manifold edge, joins two different elements, or its faces differ by more than 30 deg (`|n1.n2|`, sign-insensitive because the reader's winding is not consistent). Needle triangles and edges shorter than 1 cm are dropped (tessellation noise, leaf cards). Smooth edges (2..30 deg) are silhouette candidates: the vertex shader draws them only where one adjacent face is front- and the other back-facing (normals oriented away from the element centre). Planting / Entourage / Topography are "soft": only their silhouettes. Line weights: extra offset passes (1..3 px), colours per element.
* **View graphics**: `GET /api/m/{mid}/vg3d/{viewId}` (`rvtviewer/vg3d.py`, rvt-sheets `resolve_view(..., explain=True)`): hidden elements (view / template / filters), fill colours, transparency, line colour and weight, halftone. Applied when a view is opened (`openView` -> `__hl.loadView`), restored on close.
* **Datums**: `GET /api/m/{mid}/datums3d` (`rvtviewer/datums3d_worker.py`): level plane envelopes; levels are drawn as dashed L-shapes (the two edges at the corner farthest from the eye, recomputed on camera change), with a head symbol and label. Grids still use the overlay lines.
* **Per-view style**: `views[].display` (rvt_viewdisp / viewdisp.py) selects the style, silhouettes, hidden lines and sky / ground background when a view is opened (c3-vctl `vsFromView`).
* **Options** (`vstyle.set(id, opts)`): `edgeAngle`, `silhouettes`, `hiddenLines` off|faint|dashed (second edge pass with `GreaterDepth`), `lineWeight`, `transparency`, `halftone`, `faceColor`.
* Models over 12 M triangles open in Realistic until hidden line is chosen; edge extraction 1 M triangles ~0.7 s (worker), 3.9 M triangles 2.9 s / 1.2 GB.

## Measuring against Revit
Revit exports: `~/review-compare/revit/<file>/<viewId>.png` + `cameras.tsv` (eye, target, `style=HLR|FlatColors`).
* `tools/shot3d.py FILE VIEW CAMERA OUT --style hidden --vg VIEWID --ortho --fit --like REVIT.png` (browser) and `tools/hl_soft.py` (browser free, numba, host1) render the same view; `tools/hl_score.py REVIT.png OURS.png` registers the images (scale + shift) and reports line precision / recall / F1 (3 px tolerance); `tools/hl_table.py`, `tools/hl_soft_all.py` tabulate whole files.
* Measured (registered line F1, hidden-line views): Snowdon 43 (2024) mean 0.88 over 7 views (Framing .99, Slabs .96, Structure Only .90, CoverSheet .89, Columns .87, Foundations .80, Walls .78); Snowdon 55 (2026) mean 0.80 (Foundations .25 is a scale artefact of the score, the render matches visually). FlatColors views (Consistent Colors in Revit) are not hidden-line and score lower by design.
* Tests: `tools/style_test.py` (5-style round trip), `tools/vstyle_opts_test.py`, `tools/hl_cache_test.py`, `tools/hl_view_test.py`, `node tools/hl_worker_test.js`, `tools/hl_edge_stats.py` (numpy edge statistics per element).

## Known gaps
* Surface patterns / material graphics colours (needs reader: material surface + cut pattern colours); grey interior faces of Revit walls come from them.
* Level / grid per-view extents, level colours (filter 'Levels - Building'), grids hidden by filters: sheets filter evaluation for datums.
* Yellow framing fills depend on filter evaluation (Z Offset rules).
* Writer scenes: roofs / floors without geometry show open tops.
