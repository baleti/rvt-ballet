# rvt-viewer

Open a native Revit file (.rvt, 2020-2026) in a browser **without Revit**: orbit/pan/zoom, pick elements, inspector with stored parameters,
model tree by category/level, search, visibility, section, measure. Pure Python backend (uses the sibling `~/rvt-research` reader), Three.js front-end, fully offline.

## Run
    ./rvt-viewer open FILE.rvt            # convert (cached), serve on a free local port, open an app-mode Chromium window
    ./rvt-viewer open FILE.rvt --no-browser --port 8800
    ./rvt-viewer open FILE.rvt --workspace 178   # Hyprland: open silently on workspace 178
    ./rvt-viewer convert FILE.rvt OUTDIR  # only write model.glb / meta.json / model.sqlite
    ./rvt-viewer serve [DIR...]           # serve already converted models (default: all in ~/.cache/rvt-viewer/models)
Needs the venv: `python -m venv --system-site-packages .venv && .venv/bin/pip install cadquery-ocp mapbox-earcut` (aiohttp, numpy, scipy from the system).
First conversion of a big file takes minutes (the reader decodes every record); re-opening is seconds (raw + converted caches).

## Architecture
    .rvt --(rvt-research reader, rvtviewer/reader.py)--> records, headers, parameters
         --(rvtviewer/build.py + geom.py + brep.py + datums.py)--> element table, meshes per class, levels/grids/rooms/views
         --> model.glb   merged mesh per category (Y-up metres), per-vertex float `_EIDX` = element index, no normals (flat shading in shader)
             meta.json   columnar element table, batches (category, colour), levels, grids, rooms, views, sheets, coverage, default-hidden categories
             model.sqlite  elements + parameters (lazy inspector, parameter-value search)
    aiohttp server (rvtviewer/server.py) <--> web/app.js (Three.js r170 vendored in web/vendor, no network needed)
Viewer details: a DataTexture holds per-element state (hidden / selected / hover / ghost / fidelity); a patched material discards/colours fragments from it,
so show/hide/isolate/highlight on 100k elements is one texture upload. Picking renders `_EIDX` and depth to a 1x1 target (exact, O(1) per click).

## Geometry honesty
Every element has a fidelity tag shown in the inspector, tree, tooltip, coverage tab and the "Fidelity colours" mode:
- `solid`  decoded B-rep faces from the file (planar faces only so far)
- `param`  rebuilt from stored parametric data (approximate: wall joins/openings, roof slopes not modelled)
- `bbox`   placeholder box at the true Revit bounding box (header), oriented when the instance transform allows
- `line`   curve;  `none` nothing drawable (types, annotations, views...)
`bboxAgreement` in meta.json / inspector = IoU between our mesh and the Revit-stored bounding box (location accuracy check).

### Coverage per class (current)
| class | tier | check |
|---|---|---|
| walls (straight) | param: reference-face box | IoU 0.94-0.97 |
| floors / ceilings / pads | param: sketch prism between ref planes | IoU 0.94-0.99 |
| ducts, pipes, conduits, cable trays | param: sweep along line/arc | IoU 0.99 |
| stairs runs | solid: planar B-rep | IoU ~0.7 (support included) |
| family instances (fittings, terminals, equipment, columns, beams, doors, windows, furniture...) | bbox (oriented) | exact AABB |
| model lines | line | - |
| roofs, curved walls, flex ducts, topography, railings | bbox | todo |

## Provenance / rules
See PROVENANCE.md (no ODA-derived tables). Test samples are Autodesk files kept local in ~/rvt-research/corpus and never copied here.
