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

### Verified against Revit-computed values (tools/verify_gt.py, ground truth = gt4 dumps from real Revit, not from this project)
Walls: Unconnected Height within 5% for 94-100% of walls, Length within 5% for 89-100%; Volume median ratio 1.00 (openings/joins make 30-70% of walls deviate >5%).
Floors: Volume within 5% for 87-100% (2020/18, 2026/55, 2026/58). Location check vs Revit's stored bounding box (IoU): ducts 0.99, pipes 0.98, ceilings/cable trays 1.0, floors 0.92-1.0, walls 0.80-0.99 (header box includes hosted sweeps).

### Corpus table (tools/run_all.py; element counts are what the reader decodes)
| file | elements | drawn | solid | param | approx | bbox | line | tris | build s |
|---|---|---|---|---|---|---|---|---|---|
| 2020/18_rst_basic_sample_project | 13853 | 5794 | 8 | 14 | 1 | 1420 | 4351 | 23913 | 2.1 |
| 2020/20_Residential_Sample_Project | 7277 | 510 | 3 | 62 | 2 | 268 | 175 | 4767 | 0.8 |
| 2020/21_rst_advanced_sample_project | 13586 | 4737 | 2 | 6 | 0 | 2786 | 1943 | 37515 | 2.3 |
| 2020/23_rme_advanced_sample_project | 29132 | 10375 | 15 | 1472 | 0 | 6334 | 2554 | 128532 | 5.8 |
| 2024/42_Snowdon_Towers_Sample_HVAC | 12679 | 2777 | 0 | 1053 | 0 | 1656 | 68 | 32576 | 2.4 |
| 2024/43_Snowdon_Towers_Sample_Structural | 16571 | 2490 | 2 | 84 | 0 | 1381 | 1023 | 19804 | 2.5 |
| 2026/54_Snowdon_Towers_Sample_HVAC | 12791 | 2777 | 0 | 1053 | 0 | 1656 | 68 | 32576 | 2.4 |
| 2026/55_Snowdon_Towers_Sample_Structural | 16678 | 2490 | 2 | 84 | 0 | 1381 | 1023 | 19804 | 2.5 |
| 2026/57_Snowdon_Towers_Sample_Plumbing | 25837 | 6531 | 0 | 3232 | 0 | 3228 | 71 | 211835 | 5.5 |
| 2026/58_Snowdon_Towers_Sample_Facades | 9645 | 727 | 0 | 79 | 5 | 451 | 192 | 6628 | 1.4 |
| 2026/59_Snowdon_Towers_Sample_Site | 11834 | 1635 | 17 | 17 | 0 | 104 | 1497 | 3488 | 2.9 |

Samples 2020/2024/2026, family-heavy (2020 Residential, 2026 Facades) and MEP-heavy (2020 rme_advanced, 2024 HVAC, 2026 Plumbing) all convert and open. More files (2021-2025) converted OK via tools/batch.py, except 2021/24_rst_basic which the reader takes minutes on (reader-side).

### Performance
Synthetic 150k elements / 1.8M triangles (tools/synth.py): metadata+GLB load 1.2 s (software GL), visibility change 5 ms. Real Intel Iris Xe (app-mode Chromium): GPU pick 4.5 ms, full 120k-triangle render 13 ms at 1906x972.
Not done: true instancing (placeholders are tiny merged boxes; real symbol geometry is not in the file, see NEEDS-FROM-READER.md).

## Tests
`.venv/bin/python tests/test_geom.py`; UI: `tools/uitest1.py|uitest2.py|uitest3.py MODELDIR PORT OUTPREFIX` (headless Chromium via CDP, real mouse events, screenshots).

## Provenance / rules
See PROVENANCE.md (no ODA-derived tables). Test samples are Autodesk files kept local in ~/rvt-research/corpus and never copied here.
