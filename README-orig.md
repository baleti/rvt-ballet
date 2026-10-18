# rvt-viewer

Open a native Revit file (.rvt, 2020-2026) in a browser **without Revit**: orbit/pan/zoom, pick elements, inspector with stored parameters,
model tree by category/level, search, visibility, section, measure. Pure Python backend (uses the sibling `~/rvt-research` reader), Three.js front-end, fully offline.

## Demo (one command, any .rvt / .rte)
    ~/src/rvt-viewer/bin/rvt-view /full/path/FILE.rvt            # convert/load with the progressive "STILL PARSING" banner; app window on your CURRENT workspace, with focus
    ~/src/rvt-viewer/bin/rvt-view /full/path/FILE.rvt --sheets   # same, opening directly on the Sheets page
    ~/src/rvt-viewer/bin/rvt-view --prepare /full/path/A.rvt [B.rvt ...]   # demo prep: convert + cache, warm the sheets cache (rvt-sheets warm), print 'READY: <exact demo command>' and what is cached
    ~/src/rvt-viewer/bin/rvt-view /full/path/FILE.rvt --hide Planting,Entourage   # start with categories hidden (URL ?hide=A,B)
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

## Features added 2026-10-16
* **Annotations** (header button): the view-dependent content of a plan / section (tags, text, dimensions, grids, levels, markers, hatches) placed in model space on the 3D scene with per-category / type / element visibility, colour, line weight, text size, annotation scale, presets, picking (docs/VIEW-CONTROL.md, docs/CONTROL-API.md; built by the vctl branch, data from rvt-sheets).
* Inspector line "reader accuracy for <class>" from the corpus acceptance table (web/fidclass.json, docs/FIDELITY-FINAL.md for 2020-2026, docs/FIDELITY-2017-2019.md for the older files); full corpus table with timings (DEMO.md, docs/SWEEP.md, docs/SPEED.md); viewer mesh vs Revit per class (docs/ORACLE-SWEEP.md, tools/oracle_sweep.py).
* Revit navigation: Shift+middle-drag orbit, middle-drag pan, wheel zoom at cursor (tools/uitest12.py).
* Visual styles (header box `Style`, Revit's Visual Style menu): **Hidden line** (default: white faces, black feature and silhouette edges, faint hidden lines, view graphics / transparency / halftone from the file), Shaded, Consistent colors, Realistic (textures, shadows), Wireframe. A stored view opens in its own style (`views[].display` from the reader); `?style=realistic` or `?vs=` sets the session default. Details: web/hl.js, docs/VSTYLE-API.md.
* Views: the stored view direction points from the target to the eye (Revit's ViewDirection), so 3D views, sections and elevations look along its negative; the cut plane keeps what lies beyond it.
* tools/shot3d.py renders any view or Revit camera headless (`--style auto --edges --vg ID --sky --spec spec.json` for sheet 3D viewports); tools/review_shots.py makes the Revit/ours review pairs.

## Features added 2026-10-12 (see docs/ for details)
* Per-body geometry badge in the inspector: kind (decoded B-rep / saved mesh / parametric / box), surface types per body (plane, cylinder, cone, sphere, torus, revolution, ruled, hermite, bspline), triangles, area, closed/open, the reason when it is not true geometry; legend explains the badge. `docs/WHY-BOXY.md` lists what is still box/approximate per model and why.
* Materials and textures: per-FACE materials from the file (reader `element_mesh` 'mat', Python and Rust paths): 2020 Residential 25/25 sampled elements have exactly Revit's face-material set (tools/mat_eval.py vs the oracle's gt_mat); colours from the appearance asset (Generic and Prism/Advanced schemas) or the material colour, transparency, shininess; Revit's own swatch PNGs stored in the file (Materials tab = material browser); texture BITMAPS from a local copy of the Autodesk material library (`~/.cache/rvt-textures`, override `RVT_TEXTURE_LIB`; the .rvt only stores the paths; never shipped) at the asset's real-world scale (ft/in units), offset and rotation; without the library, flat swatches from the file or procedural patterns (labelled fallback). Inspector: colour / swatch / texture provenance per material and 'per face (reader)' vs 'per body' material source.
* Plug-ins: `docs/PLUGINS.md` (rvt-sheets mounts at /sheets/, drawing links, postMessage select/isolate).
* `docs/SHOWCASE.md` + `tools/showcase.py`: which file shows which surface type; headless screenshots in screenshots/showcase/ (not committed).
* Mesh quality check: reader meshes of curved solids whose triangle area disagrees with the analytic area are labelled approximate (torus), see NEEDS-FROM-READER.md section 10.

## Features added 2026-10-15
* Section caps (poche): a section plane / box or an opened plan view fills the cut solids dark, like a Revit section (stencil parity per clip plane; open shells and sheet-like categories such as topography are excluded via `meta.openBodies`); 'caps' checkbox in the section panel.
* Sun shadows (Shadows button, key L): the sun follows the view azimuth; the shadow map is redrawn only on visibility / section / model change or a turn of more than 8 deg.
* Bump maps: Revit `*_bump_map` bitmaps from the local library with their own real-world scale and `*_bump_amount` (2020 Residential: 24 materials, e.g. siding boards, concrete).
* Fit frames the visible elements; share links with `hc=` refresh the tree.

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
Every element has a fidelity tag shown in the inspector, tree, tooltip, Coverage tab and the "Fidelity colours" mode:
- `solid`  the reader's mesh for the element (saved-graphics triangles or decoded B-rep faces, per body and per face material)
- `param`  rebuilt by the viewer from stored parametric data (fallback only; extents checked against the stored bbox, exact shape unproven)
- `bbox`   placeholder box at the Revit-stored bounding box (the reader has no usable mesh)
- `void`   instance with no 3D solid in Revit (void openings, reference families, QTY markers): drawn as an outline, not counted as box-only
- `line`   curve;  `none` nothing drawable (types, annotations, views...)
`bboxAgreement` in meta.json / inspector = IoU between our mesh and the Revit-stored bounding box.

### Accuracy vs Revit: the reader's FINAL per-class table (c4-geometry, 2026-10-14)
Source: ~/rvt-research/NOTES.md section "FINAL per-class / per-year geometry table" and FID_TABLE_FINAL.txt (60 of the 61 gt4 Revit dumps, corpus files 2020-2026, Fine detail first then Medium, <= 400 elements per class per file). Three honest buckets per element:
- **reader-accurate**: decoded solid with Revit's Volume within 2% (where Revit gives no Volume: bbox IoU >= 0.95 vs the stored bbox; zero-volume sheets/analytical surfaces validated by area + bbox against the oracle)
- **mesh, unproven** (reader's "true-off"): a mesh exists but the criteria fail
- **box-only**: no usable mesh, the viewer draws the stored bbox

Excluded (listed in the reader's footers): type/symbol definitions, curtain/stacked wall hosts (geometry is in their panels/mullions), elements with an empty stored bbox, void families, placeholder ids, unplaced rooms.

| class | n | reader-accurate | mesh, unproven | box-only | median IoU | median abs. volume error |
|---|---|---|---|---|---|---|
| FamilyInstance | 14495 | 97.8% | 1.4% | 0.8% | 0.998 | 0.00% |
| CurveElem (model lines) | 13743 | 99.9% | 0.0% | 0.1% | 1.000 | - |
| Ducts / pipes / conduits / flex ducts | 11696 | 100% | 0% | 0% | 1.000 | - |
| SWall (walls) | 2592 | 99.3% | 0.1% | 0.6% | 0.977 | 0.00% |
| RoomElem | 1605 | 99.4% | 0.6% | 0.0% | 1.000 | 0.00% |
| Ceiling | 693 | 100% | 0% | 0% | 1.000 | 0.00% |
| WallSweep | 452 | 100% | 0% | 0% | 1.000 | - |
| Floor | 442 | 100% | 0% | 0% | 1.000 | 0.00% |
| BaseRailing | 259 | 100% | 0% | 0% | 0.937 | - |
| DPart (parts) | 184 | 99.5% | 0.0% | 0.5% | 1.000 | 0.00% |
| Stairs (+ runs, supports) | 128 | 100% | 0% | 0% | 0.61-1.0 | - |
| Roofs (ProfileRoof, FaceRoof) | 61 | 100% | 0% | 0% | 1.000 | 0.00% |
| ContFooting | 52 | 100% | 0% | 0% | 1.000 | 0.00% |
| Toposolid / SiteSurface / BuildingPad | 79 | 97% | 1% | 1% | 1.000 | 0.00% |
| SweepHost (fascias, gutters) | 41 | 92.7% | 0.0% | 7.3% | 0.039 | 0.00% |
| Text3dElem (model text) | 13 | 76.9% | 23.1% | 0.0% | 0.957 | - |

Per year, FamilyInstance is 96-99% reader-accurate (2025/2026: 2% box-only = nested pile/void families); every class with a meaningful population is >= 96% in total. Residuals named by the reader: 2 rooms with zero-width slits, Facades 'Flex' columns 3% low, 3 Residential fascias carry a solid Revit's export lacks, family profile polygons are not stored, texture bitmaps are not in the .rvt (library paths only). Rebar is outside the table (no Volume-bearing graphics): centre-lines vs Revit's GetCenterlineCurves are exact for 346/346 sets (2020 rst_basic), 11/11 (rst_advanced), 12/14 (2024/2026 Structural).

What the viewer adds on top: it draws exactly these reader meshes (per body, per face material), falls back to `param` / `bbox` only where the reader has nothing, and reports its own per-file shares (true / matched / approximate / box) for all 78 corpus files 2017-2026 in docs/SWEEP.md. The older viewer-side acceptance run (docs/ACCEPTANCE-STATUS.md, tools/accept_eval.py) predates the reader's final table and is superseded by it.

### Provisional constants
`OPENING_SHRINK` (0.2 ft trimmed from door/window bounding boxes to approximate the real hole) and `ROOF_ATTACH_FRACTION` are tuning for the parametric wall fallback only; walls normally come from the reader's mesh, which already carries the real cut.

### Safety
Every conversion runs under `systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0` with nice (cli does it for `open`/`convert`; `tools/capped.sh CMD...` for scripts; RVT_MEM_CAP overrides, RVT_NO_CAP disables). Evaluations stream results to disk one file at a time under a cap.

### Corpus table
All 78 corpus files 2017-2026 convert and pass the functional test: docs/SWEEP.md (tools/sweep.py + tools/sweep_table.py), summary in DEMO.md.

### Conversion pipeline and timings (host3, 2026-10-12; tools/timings.py: each model in its own capped process)
Stages (progress.json, shown in the UI): reading -> tables (+sqlite) -> preview (boxes, usable immediately) -> geometry (saved-graphics meshes decoded in forked workers, then the remaining builders in forked workers; disk-cached by reader stamp + geometry source) -> packing (meshes + materials).
**First open is progressive**: `open` returns at once; the page shows a STILL PARSING banner (stage, counters such as `Reading saved graphics 233 / 535 elements`, live elapsed time and ETA, spinner driven by a local clock, so it never looks frozen), a PARTIAL MODEL watermark, levels/grids/boxes first, then finished meshes replacing translucent ghost boxes every ~12 s while the rest is decoded. When the model is complete the banner says so. A model that is already converted loads from the cache and says `Loaded from cache - reader version X - N elements in 0.x s`.
| model | file | elements | cold open: decode + geometry (viewer caches bypassed) | stage seconds (quick table / reader / tables / geometry) | first picture (levels + boxes) |
|---|---|---|---|---|---|
| residential-2020 | 10 MB | 7277 | 8.9 s (was 19 s) | 0.03 / 0.8 / 0.2 / 6.8 | ~1 s |
| facades-2026 | 53 MB | 9645 | 48 s (was 60 s) | 0.07 / 1.0 / 0.4 / 44 | ~1-3 s |
| hvac-2024 | 22 MB | 12679 | 92 s (was 142 s) | 1.1 / 2.4 / 2.7 / 84 | ~1-3 s |
| structural-2024 | 28 MB | 16571 | 30 s (was 121 s) | 0.1 / 1.2 / 0.9 / 23 | ~1 s |
| mep-2020 | 35 MB | 29132 | 133 s (6.8 GB peak; the Python path was OOM-killed at 8 GB) | 3.9 / 5.5 / 5.5 / 115 | ~4 s |
Cache-hit page load (headless, software GL, 1280x720): 1.4-2.4 s. Measured on host3 under a load average of 7-10 from other sessions, 2026-10-12 (Rust fast path on; `RVT_NOFAST=1` forces the Python reader).
The reader's own caches (xcache) are used as shipped; the reader's Rust fast paths (extract, schemas, g103) are on by default and make the cold decode seconds instead of minutes. The geometry stage (the reader's element_mesh in Python, now 6 forked workers) is what remains; rvt-core is porting it to Rust. The geometry stage is now mostly the Rust mesh stream plus the viewer's own per-mesh work (topology check, materials, body summary, ~9 s on Facades).

### Performance
Real GPU (Intel Iris Xe, headless Chromium via ANGLE/Vulkan, no window; `tools/perftest.py DIR PORT vulkan`, 1280x720, ms per synced full frame, 2026-10-15):
| model | triangles | frame | frame with shadow-map redraw (only on turns > 8 deg / visibility change) | section plane + caps | GPU pick |
|---|---|---|---|---|---|
| 2023 rme_basic | 2.15 M | 14.9 | 35.9 | 23.7 | 17.9 |
| 2019 Arch Link | 0.86 M | 13.0 | 35.0 | 15.1 | 11.2 |
| 2024 Snowdon Structural | 0.67 M | 16.6 | 26.1 | 12.3 | 12-20 |
| 2026 Snowdon Facades | 0.29 M | 7.5 | 12.2 | 6.9 | 8.5 |
Synthetic 150k elements / 1.8M triangles (tools/synth.py): metadata+GLB load 1.2 s (software GL), visibility change 5 ms. Real Intel Iris Xe (app-mode Chromium): GPU pick 4.5 ms, full 120k-triangle render 13 ms at 1906x972.
Not done: true instancing (placeholders are tiny merged boxes; real symbol geometry is not in the file, see NEEDS-FROM-READER.md).

## Tests
`.venv/bin/python tests/test_geom.py`; UI: `tools/uitest1.py|uitest2.py|uitest3.py MODELDIR PORT OUTPREFIX` (headless Chromium via CDP, real mouse events, screenshots).

## Provenance / rules
See PROVENANCE.md (no ODA-derived tables). Test samples are Autodesk files kept local in ~/rvt-research/corpus and never copied here.
