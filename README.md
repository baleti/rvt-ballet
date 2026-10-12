# rvt-viewer

Open a native Revit file (.rvt, 2020-2026) in a browser **without Revit**: orbit/pan/zoom, pick elements, inspector with stored parameters,
model tree by category/level, search, visibility, section, measure. Pure Python backend (uses the sibling `~/rvt-research` reader), Three.js front-end, fully offline.

## Demo (one command, any .rvt / .rte)
    ~/src/rvt-viewer/bin/rvt-view /full/path/FILE.rvt            # convert/load with the progressive "STILL PARSING" banner; app window on your CURRENT workspace, with focus
    ~/src/rvt-viewer/bin/rvt-view /full/path/FILE.rvt --sheets   # same, opening directly on the Sheets page
    ~/src/rvt-viewer/bin/rvt-view --prepare /full/path/A.rvt [B.rvt ...]   # demo prep: convert + cache, warm the sheets cache (rvt-sheets warm), print 'READY: <exact demo command>' and what is cached
    alias rvt=~/src/rvt-viewer/bin/rvt-view                      # optional; ./rvt-viewer open FILE.rvt is the same command (agents: --workspace N --no-browser --port P)
The toolbar has a **Sheets** button (and `drawing` links in the Views tab): it embeds the rvt-sheets page (sheet list, sheet render with viewports, click a viewport to open that view, pan/zoom) full size over the 3D view; **Model (3D)** goes back. Files without sheets say so ("This file has no sheets (N views only)"); if the optional modules are missing (`pip install shapely numba` in .venv) the button reads "Sheets (unavailable)" with the reason instead of crashing. Clicking an element in a drawing selects and frames it in 3D. `--prepare` converts and caches the model and calls `rvt-sheets warm FILE` when that command exists (until then it prints that the sheets are not pre-warmed; they render on first open). A small `model cached - sheets cached` badge next to the model selector shows what came from the caches. Plug-in interface: docs/PLUGINS.md.
Verified end to end (tools/uitest10.py, headless; time to a usable first picture / complete model / sheets page ready): 2020 Residential (10 MB): 7.9 s / 27.9 s (Python path, before the Rust fast path) / 2 s, 4 sheets 41 views; 2024 Snowdon Structural (28 MB): 6.5 s / 57 s cold, 8.5 s / 15.5 s warm geometry / sheets page 5 s (its own progress card first), 12 sheets 104 views; 2026 Construction template (.rte): 2.4 s / 4.0 s, no sheets (39 views). With the Rust fast path the quick element table (levels + one box per element) appears within ~1-3 s of opening.

## Run
    ./rvt-viewer open FILE.rvt            # convert (cached), serve on a free local port, open an app-mode Chromium window
    ./rvt-viewer open FILE.rvt --no-browser --port 8800
    ./rvt-viewer open FILE.rvt --workspace 178   # Hyprland: open silently on workspace 178
    ./rvt-viewer convert FILE.rvt OUTDIR  # only write model.glb / meta.json / model.sqlite
    ./rvt-viewer serve [DIR...]           # serve already converted models (default: all in ~/.cache/rvt-viewer/models)
Needs the venv: `python -m venv --system-site-packages .venv && .venv/bin/pip install cadquery-ocp mapbox-earcut` (aiohttp, numpy, scipy from the system).
First conversion of a big file takes minutes (the reader decodes every record); re-opening is seconds (raw + converted caches).

## Features added 2026-10-12 (see docs/ for details)
* Per-body geometry badge in the inspector: kind (decoded B-rep / saved mesh / parametric / box), surface types per body (plane, cylinder, cone, sphere, torus, revolution, ruled, hermite, bspline), triangles, area, closed/open, the reason when it is not true geometry; legend explains the badge. `docs/WHY-BOXY.md` lists what is still box/approximate per model and why.
* Materials and textures: per-FACE materials from the file (reader `element_mesh` 'mat', Python and Rust paths): 2020 Residential 25/25 sampled elements have exactly Revit's face-material set (tools/mat_eval.py vs the oracle's gt_mat); colours from the appearance asset (Generic and Prism/Advanced schemas) or the material colour, transparency, shininess; Revit's own swatch PNGs stored in the file (Materials tab = material browser); texture BITMAPS from a local copy of the Autodesk material library (`~/.cache/rvt-textures`, override `RVT_TEXTURE_LIB`; the .rvt only stores the paths; never shipped) at the asset's real-world scale (ft/in units), offset and rotation; without the library, flat swatches from the file or procedural patterns (labelled fallback). Inspector: colour / swatch / texture provenance per material and 'per face (reader)' vs 'per body' material source.
* Plug-ins: `docs/PLUGINS.md` (rvt-sheets mounts at /sheets/, drawing links, postMessage select/isolate).
* `docs/SHOWCASE.md` + `tools/showcase.py`: which file shows which surface type; headless screenshots in screenshots/showcase/ (not committed).
* Mesh quality check: reader meshes of curved solids whose triangle area disagrees with the analytic area are labelled approximate (torus), see NEEDS-FROM-READER.md section 10.

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

### Fidelity table (tools/regress.py, building-geometry elements only: analytical/reference/room/annotation-like categories excluded)
`true + matched` (formerly "exact"; the word "exact" is reserved for the reader's ACCURATE definition: volume within 2 % of Revit or bbox IoU >= 0.95, see docs/ACCEPTANCE-STATUS.md) = solid (decoded B-rep) + matched (rebuilt from stored data AND extents agree with the bounding box Revit stored: IoU >= 0.97, or inside it spanning >= 93% of its two largest dimensions); `approximate` = rebuilt but not matching / footprint-only; `box only` = placeholder at the stored bounding box.
| model | elements | true geometry (B-rep / saved mesh) | parametric, extents match | approximate | box only |
|---|---|---|---|---|---|
| residential-2020 | 218 | 93% | 0% | 2% | 6% |
| structural-2024 | 1371 | 95% | 0% | 0% | 5% |
| mep-2020 | 6879 | 79% | 20% | 1% | 1% |
| hvac-2024 | 2630 | 59% | 41% | 0% | 0% |
| facades-2026 | 523 | 98% | 0% | 1% | 1% |
Measured 2026-10-12 (afternoon) with the reader's updated mesh path (earlier values in git history). Changes since the previous table: per-body (nid/fid) meshes, flex ducts from their Hermite curves (HVAC box 1% -> 0%), curtain grid lines as lines, joist/beam systems are layout containers without geometry and no longer counted (Structural 1447 -> 1371), MEP re-measured after its class census was rebuilt. Remaining box-only: Rebar (no saved graphics), family instances whose symbol has no graphics, reference points/hubs (see NEEDS-FROM-READER.md section 8). In MEP and HVAC the "parametric" share is ducts and pipes rebuilt from stored curves/sections: extents match Revit's bounding box but the exact shape is unproven.

Walls, floors, ceilings and roofs now use the reader's saved-graphics meshes (they match Revit's volume within 2% for 92-100% of 2020 residential elements vs 57% / 0% for the parametric rebuild, which stays as fallback); doors/windows/trees count as true geometry when the mesh lies inside the stored bounding box. Only the first column is geometry decoded from the file's own faces; "parametric, extents match" (ducts, pipes, walls, floors rebuilt from stored curves/sections) matches Revit's stored bounding box but its exact shape is unproven.
Family instances now come from the reader's saved-graphics triangle meshes (rvt_geometry 'mesh_approx': planar + cylindrical faces; ruled/revolved/NURBS faces still missing); box-only is what the reader has no saved graphics for. `tools/compare_gt.py` + the viewer's Compare button measure deviation against Revit oracle files (rvt-research/gt_geom). GEOMETRY_API.md reviewed: for every class it covers (walls, floors, ceilings, ducts..., instances as boxes) the API is 'approx'/'box' and the viewer's own builders already include joins, openings, layers and slopes, so nothing was switched to it; `tools/check_api.py FILE` compares both and flags classes where the API becomes 'exact'.

### Volume vs Revit (tools/verify_gt.py; share within 5% of Revit's Volume)
| sample | walls | floors | ceilings | roofs |
|---|---|---|---|---|
| 2020 MEP | 81% (133) | 100% (21) | 100% (43) | - |
| 2026 Structural | 68% (56) | 93% (30) | - | - |
| 2020 Residential | 43% (49) | 100% (6) | 100% (1) | 0% (2, median 1.09) |
| 2026 Facades | 45% (78) | 100% (1) | - | 80% (5) |
Walls: butt/miter joins from the stored join lists, hosted door/window/generic-void openings (doors/windows shrunk 0.2 ft per side, fitted on gt4), compound-structure layers, tops joined to roofs follow the roof. Floors: nested loops, stored Revit extent for flat slabs, open B-rep shells not accepted as solid. Weakest group: gable walls joined to roofs.
Reader API status (GEOMETRY_API.md, rvt_brep.py, new rvt_mesh.py): still no family solids. Wired in: the reader's shell split (rvt_mesh.components) decides which B-rep bodies are closed solids (open shells become approximate); `tools/check_mesh.py` cross-checks its tessellation against ours (18/19 bodies agree on the 2020 MEP sample); `tools/check_api.py` compares API confidence per class.

### Acceptance status (ACCEPTANCE.md): per class, per year
See `docs/ACCEPTANCE-STATUS.md` (regenerate with `tools/accept_table.py` after `tools/accept_all.sh` + `tools/accept_retry.sh`). Caveat: classes whose volume is not measurable in gt4 (rooms, topography...) can show DONE on IoU alone.

### Provisional constants
`OPENING_SHRINK` (0.2 ft trimmed from door/window bounding boxes to approximate the real hole) was fitted against Revit volumes in gt4: it is tuning, not modelling. Openings should come from the families' real cut bodies (`m_complexCutGeoms`, already used when a symbol has one); the constant only covers doors/windows without them and will be removed once symbol geometry decodes. `ROOF_ATTACH_FRACTION` is likewise provisional.

### Memory discipline for evaluations
`tools/accept_all.sh` runs ONE file at a time under a 3.5 GB cap, waits while MemAvailable < 5 GB, and `accept_eval.py` evaluates element by element (no model build, no worker pool, mesh freed after its metrics, aborts above 3.3 GB RSS). Results are streamed to `~/.cache/rvt-viewer/accept/*.json`; finished files are skipped on restart.

### Safety
Every conversion runs under `systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0` with nice (cli does it for `open`/`convert`; `tools/capped.sh CMD...` for scripts; RVT_MEM_CAP overrides, RVT_NO_CAP disables).

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

### Conversion pipeline and timings (remote-host, 2026-10-12; tools/timings.py: each model in its own capped process)
Stages (progress.json, shown in the UI): reading -> tables (+sqlite) -> preview (boxes, usable immediately) -> geometry (saved-graphics meshes decoded in forked workers, then the remaining builders in forked workers; disk-cached by reader stamp + geometry source) -> packing (meshes + materials).
**First open is progressive**: `open` returns at once; the page shows a STILL PARSING banner (stage, counters such as `Reading saved graphics 233 / 535 elements`, live elapsed time and ETA, spinner driven by a local clock, so it never looks frozen), a PARTIAL MODEL watermark, levels/grids/boxes first, then finished meshes replacing translucent ghost boxes every ~12 s while the rest is decoded. When the model is complete the banner says so. A model that is already converted loads from the cache and says `Loaded from cache - reader version X - N elements in 0.x s`.
| model | file | elements | cold open: decode + geometry (viewer caches bypassed) | stage seconds (quick table / reader / tables / geometry) | first picture (levels + boxes) |
|---|---|---|---|---|---|
| residential-2020 | 10 MB | 7277 | 8.9 s (was 19 s) | 0.03 / 0.8 / 0.2 / 6.8 | ~1 s |
| facades-2026 | 53 MB | 9645 | 48 s (was 60 s) | 0.07 / 1.0 / 0.4 / 44 | ~1-3 s |
| hvac-2024 | 22 MB | 12679 | 92 s (was 142 s) | 1.1 / 2.4 / 2.7 / 84 | ~1-3 s |
| structural-2024 | 28 MB | 16571 | 30 s (was 121 s) | 0.1 / 1.2 / 0.9 / 23 | ~1 s |
| mep-2020 | 35 MB | 29132 | 133 s (6.8 GB peak; the Python path was OOM-killed at 8 GB) | 3.9 / 5.5 / 5.5 / 115 | ~4 s |
Cache-hit page load (headless, software GL, 1280x720): 1.4-2.4 s. Measured on remote-host under a load average of 7-10 from other sessions, 2026-10-12 (Rust fast path on; `RVT_NOFAST=1` forces the Python reader).
The reader's own caches (xcache) are used as shipped; the reader's Rust fast paths (extract, schemas, g103) are on by default and make the cold decode seconds instead of minutes. The geometry stage (the reader's element_mesh in Python, now 6 forked workers) is what remains; rvt-core is porting it to Rust. The geometry stage is now mostly the Rust mesh stream plus the viewer's own per-mesh work (topology check, materials, body summary, ~9 s on Facades).

### Performance
Synthetic 150k elements / 1.8M triangles (tools/synth.py): metadata+GLB load 1.2 s (software GL), visibility change 5 ms. Real Intel Iris Xe (app-mode Chromium): GPU pick 4.5 ms, full 120k-triangle render 13 ms at 1906x972.
Not done: true instancing (placeholders are tiny merged boxes; real symbol geometry is not in the file, see NEEDS-FROM-READER.md).

## Tests
`.venv/bin/python tests/test_geom.py`; UI: `tools/uitest1.py|uitest2.py|uitest3.py MODELDIR PORT OUTPREFIX` (headless Chromium via CDP, real mouse events, screenshots).

## Provenance / rules
See PROVENANCE.md (no ODA-derived tables). Test samples are Autodesk files kept local in ~/rvt-research/corpus and never copied here.
