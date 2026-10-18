# PROGRESS

## 2026-10-11 milestone 1 (repo, pipeline, viewer)
- Repo created, reader adapter (`rvtviewer/reader.py`) imports ~/rvt-research read-only, one shared extraction pass, raw cache in ~/.cache/rvt-viewer.
- Converter (`rvtviewer/build.py`) -> `model.glb` (batched per category, per-vertex element index `_EIDX`, no normals), `meta.json` (tree, levels, grids, rooms, views, sheets, coverage), `model.sqlite` (elements + all parameters, lazily queried).
- Server (aiohttp) + Three.js viewer: orbit/pan/zoom, GPU picking (ID + depth pass), hover tooltip, selection highlight + bbox, inspector, tree by category/level, search (+ parameter values), category/level/element visibility, isolate, section plane, measure, level planes/grids/rooms, coverage panel, fidelity colour mode.
- Headless Chromium CDP tests (`tools/cdp.py`, `tools/uitest*.py`): real mouse click -> inspector, search, tree checkbox, section, measure verified.
- Directive received: no ODA-derived data. Category table regenerated from Revit gt4 dumps (`tools/make_category_names.py`), see PROVENANCE.md.

## 2026-10-11 milestone 2 (geometry classes)
- Findings about the file: Revit does NOT store final solids for walls/floors/MEP/family instances; it stores parametric inputs plus reference faces. ElementHeader carries Revit's own world bounding box for every geometric element.
- Walls: reference-face planes give exact extents (IoU vs header bbox 0.94-0.97, mitred ends/openings not modelled).
- Floors/ceilings/pads: sketch outline (VarSketch -> CurveElem) extruded between top/bottom reference planes (sloped planes followed). IoU 0.94-0.99.
- Ducts/pipes/conduits/trays: line/arc driver + width/height/diameter, IoU 0.99.
- Family instances: placeholder box at true bbox, oriented via instance transform when rotated.
- Planar B-rep `Geometry` objects (Face/EdgeLoop/Edge with UV end points) decoded (`rvtviewer/brep.py`): real faces for stairs runs ('solid').

## 2026-10-11 milestone 3
- Curved walls, cylindrical B-rep faces, roofs as footprint prisms ('approx'), grids from datum planes, Family:Type names, sheet->view links, level dedupe, ghost isolate, help panel.
- Verified vs Revit values (verify_gt.py), real-GPU run in an app-mode window on Hyprland workspace 178 (silent, no focus change), 150k-element synthetic stress test.
- Open: family symbol solids (needs reader), roof slopes, room outlines, wall openings, true instancing.

## 2026-10-11 milestone 4
- Staged non-blocking conversion with progress UI and box preview; parallel + cached geometry; cache keys include reader stamp (any rvt*.py / GEOMETRY_API.md change) and converter source; stale-model banner + reconvert.
- Geometry: sloped roofs (stored per-edge slope), walls with hosted door/window/generic-void openings and tops joined to roofs (OpenCascade booleans), layered walls/floors/ceilings with material colours, curved walls, B-rep cylinders.
- Coverage tab: exact / approximate / box percentages, by category or Revit class; click a row to isolate it in fidelity colours. Screenshot regression set: tools/regress.py -> screenshots/regress (git-excluded).
- Timings table in README (cold/warm, 6 MB and 40 MB).

## 2026-10-11 milestone 5 (usage limit reached here)
- Floors fixed: nested loops (outer/hole by containment), stored Revit extent for flat slabs, open B-rep shells no longer labelled solid. Floor volume vs Revit: median 1.00, 93-100% within 5% (2020 MEP was 19%).
- Walls: door/window openings shrunk 0.2 ft (fitted on gt4); wall volume within 5%: MEP 81%, Structural 68%, Residential 43%, Facades 45%. Gable walls joined to roofs still the weak group.
- Features: open plan/section/3D views from stored frames, section plane + box, URL state (camera, selection, hidden categories, section, view), snapping measure, level/category/phase isolation, ? help overlay, model picker.
- Tests: tests/run.sh (unit + smoke), tools/uitest6.py (features, all pass).
- Reader B-rep API: no family solids yet, nothing to wire; fidelity table unchanged in kind (box-only dominated by family instances).

## 2026-10-11 acceptance work (ACCEPTANCE.md / OBJECTIVES.md)
- tools/accept_eval.py + accept_all.sh (2 files at a time, 5 GB cap, nice) compute per-class true / parametric-unproven / approximate / box-only, bbox IoU>=0.95 and volume<=2% error (gt4 Volume) for ALL 42 corpus .rvt files 2020-2026; tools/accept_table.py writes docs/ACCEPTANCE-STATUS.md (per class, per year, DONE flag).
- gt_geom oracle (session 181) wired into tools/compare_gt.py: kwalls.rte plain walls IoU 1.0 / volume ratio 1.0 (5 walls); stair run rosetta: StairsRun/Supports IoU 0.85-1.0 (approx -> mesh in the "var" file), BaseRailing IoU 0.56 (reader mesh partial).
- Baseline (first 3 files, 2020): walls 21% within 2% volume, floors/ceilings 100%, family instances 77% true geometry but only 19% volume-accurate (saved-graphics meshes are not always closed / may omit voids), curtain grid lines, hubs, reference points, filled regions, rebar, analytical elements still box-only.

## 2026-10-12 evening (c4-viewer, continues session 187): materials milestone
- Per-face materials: reader `element_mesh` 'mat' (Python + Rust stream) consumed per triangle. tools/mat_eval.py vs Revit (gt_mat FMAT): 2020 Residential 0/25 -> 25/25 elements with Revit's exact face-material set (windows get Glass + Sash, walls Siding / Gypsum, roofs Wood Shake).
- Revit's own swatch PNGs (AppearanceAssetElem.m_pThumbnail) per material: Materials tab is a material browser with swatches (124 in Residential), click for provenance.
- Texture bitmaps: local copy of the Autodesk material library (~/.cache/rvt-textures, from the oracle VM, local only, never committed); colour channels only (generic_diffuse, *_color), real-world scale with AProperty units (3 = ft, 6 = in; earlier inches were read as feet, e.g. ceiling tiles 192 ft), offset, rotation. Residential: 31 materials with real bitmaps; flat swatches used as seamless tiles when no bitmap.
- Toposurface material from unnamed ElementId parameters (grass/asphalt/gravel now right), property lines as lines, symbol-without-graphics instances (void openings, reference families) as outlines.
- Demo: an older complete conversion opens instantly after reader changes (small 'newer reader available' chip); DEMO.md; label de-overlap.
- Tests: tools/functest.py (server + sheets plug-in functional checks per model), tools/sweep.py (+ sweep_table.py -> docs/SWEEP.md) queued on remote-host for all 77 corpus files.

## 2026-10-13 (c4-viewer): geometry completeness + robustness
- CORPUS SWEEP (remote-host, docs/SWEEP.md): 78 / 78 files 2017-2026 convert and pass the functional test (meta, glb, materials, inspector, search, sheets + view SVG).
- Box-only gone on the reference models: rebar from the reader's shape definitions (2020 rst_basic box-only 44% -> 0%), 'void' class for instances with no 3D solid in Revit (void openings, reference families, QTY markers: outline only, not box-only), model groups / area-reinforcement systems / graphics styles are containers. Structural 2024: 100% true geometry; Facades 2026 99.8% true, 0 box; HVAC 2024 100% true (ducts mesh-first from saved graphics, cold 92 s -> 23-32 s).
- Speed: Rust refined_volume drop-in (Facades cold 36 s -> 16 s), vectorised body_summary (Structural geometry 7.7 -> 6.1 s), rvt_fast.Doc default (fork deadlock fixed upstream).
- Robustness: Rust panics fall back to the Python reference (found: refined_volume panic on rme_advanced, NEEDS 17); workers bounded by the memory cap; sweep conversions each in a capped scope.
- Colour fidelity: sRGB -> linear glTF colours, Prism (Advanced) appearance colours, opaque window frames, MEP category colours, Spaces hidden by default.
- Tests: functest (server + sheets) per corpus file on remote-host (58/58 non-MEP-advanced files pass so far), uisweep (browser render) 9/9 one model per year 2017-2026.

## 2026-10-15 (c2-viewer, continues c4-viewer)
- README accuracy section replaced by the reader's FINAL per-class table (three buckets: reader-accurate / mesh-unproven / box-only); stale viewer tables removed. docs/SWEEP.md regenerated (it was stale: rst_basic 2018-2023 are 100% true geometry, not 44% box).
- 2017 rebar: requested (NEEDS 19), decoded by c2-geometry the same day: 2017 rst_basic 14% box-only -> 0%.
- Sun shadows: toggle button + key L, sun 50 deg left of the view and 40 deg high, shadow map redrawn only when visibility / section / model change or the view turns > 8 deg (hover/selection do not redraw it); hidden and ghosted elements cast no shadow (custom depth material); section planes clip shadows.
- c2-rust tip adopted: body_materials skipped when every triangle has a reader material (Residential glb byte-identical, geometry stage 3.3 -> 1.7 s).
- Share links with `hc=` now refresh the tree checkboxes. demo_smoke.sh picks the model by file name.
- Checked: tint (common_Tint) is unused in the 3 demo files (one white tint): not worth wiring. 2026 Site converts in 6.9 s on remote-host (the sweep's 41 s was contention).
- Section caps (poche): where a section plane / box cuts a solid, the cut is filled dark like a Revit section (stencil parity per clip plane, since reader winding is not consistent); 'caps' checkbox; box caps skipped above 1.5M triangles.
- CategoryElem (Revit category objects) never drawn: Residential's 'Walls' category object carried a foundation wall's bbox and z-fought it (moire); Residential now 100% true geometry, 0 box.
- Fit frames the visible elements (percentile box), not the whole site.
- convert: OCP / scipy / matplotlib imported in a thread after the quick preview (c2-rust NEEDS 19).
- Writer scenes: stale saved graphics on copied columns reported to c2-writer (NEEDS-FROM-ORACLE.md).
- demo-ready = d28ff71 (smoke on all three demo files).
- Bump maps from the library (24 in Residential), plan views capped correctly (open shells excluded). demo-ready = 56259c3.
- Prism appearances textured (opaque_albedo bitmaps, unit-less Prism scales = inches): 2026 Facades bricks / stained wood / quartz from the library (5 -> 35 bitmaps). demo-ready = 6e5bb48.
- Sweep 121/121, all 78 corpus files < 0.5% box-only. Real-GPU frame times (README): 2.15 M triangles 14.9 ms/frame.
- Asked c2-sheets (rvt-sheets HOOKS.md) to serve the newest older complete sheets cache after reader changes.
- 2026-10-15 (c4-viewer): plan/section/elevation views framed + clipped to the stored crop region; 3D views clip to stored section box; sheets badge notes stale. NEXT: rerun --prepare + smoke before re-tagging demo-ready (sheets warm on remote-host failed: remote-host memory).
- 2026-10-15 (c4-viewer): smooth vertex normals (35 deg crease; RVT_SMOOTH=0 disables), rosetta oracle table in docs/SHOWCASE.md (volume/area ratios 0.985-1.0), compare_gt area ratio. demo-ready re-smoked.

## 2026-10-15 c5-viewer
* Task B re-verified: tools/uitest12.py (real input events) ALL OK on 2020 Residential (middle pan, Shift+middle orbit, wheel zoom, right-drag inert, Alt fallbacks, dbl-middle fit). Note: MODELDIR must be one model's cache directory.
* SHOWCASE revolve/sweep/blend/torus table (volume and area ratio vs Revit 0.985-1.0) already in docs/SHOWCASE.md.
* Corpus table in DEMO.md (121/121) is from the older converter; re-sweep vsweep4 queued by tools/queue_vsweep.sh, waiting for remote-host MemAvailable >= 11 GB.

## 2026-10-15 c2-vctl (branch vctl, worktree ~/src/rvt-viewer-vctl)
* View control v1 (commits d27fadc..): header button "Annotations" opens a floating panel; overlay of the drawn view (rvt-sheets primitives) placed in model space on the 3D scene.
  Files: web/viewctl.js (overlay + panel + picking + presets), rvtviewer/viewctl.py (HTTP API), rvtviewer/vscene_worker.py (rvt-sheets ViewDrawer in its own venv, one process per file),
  rvtviewer/vcache.py (content-keyed scene cache, valid across hosts), tools/vctltest.py (regression, headless), tools/vc_warm.sh (pre-generate scenes on remote-host), docs/CONTROL-API.md (contract).
* Controls: annotation scale 1:N (exact re-render), detail level, view template on/off, filters on/off, plan cut plane height, phase + phase filter, crop on/off (model content only),
  text on/off / size x / font, line weight x / min px, placement (on top, lift, opacity, hide 3D model underneath); visibility by layer / category+subcategory / class / element; colour + line weight
  override per category and element; picking (hover tooltip, click highlight, stored fields, hide element/category/type); presets (server file + localStorage), per-view autosave, JSON export;
  `?vc=VIEWID&vcp=PRESET` opens a view with a preset. Model API: window.vctl.
* Touches shared files minimally: web/app.js (retrying import of viewctl.js, window.__dirty/__world, pickAt keeps world.visible), rvtviewer/server.py (viewctl.register).
* Tests: tools/vctltest.py URL VIEWID (ALL OK on Residential plan 'first floor'); demo smoke OK (Residential, port 8852).
* Host rules (user, permanent): no servers/workers left running on remote-host; any scene generation of big files only via tools/vc_warm.sh (remote-host, h1run) and list the job in ~/demo-state/H1-QUEUE.md. Re-warm needed after rvt-sheets/worker code changes (cache key is content based; stale caches are served with a "redraw now" button).
* Latest: depth-rank painter order (masks), stale cache fallback, part visibility, datums replace native grids; UI tested on Residential (plan + section) with tools/vctltest.py; Structural L2 shows grids 1-9/A-E and tags.
* 2026-10-16 (c5-viewer): after merging vctl 7011f97, tools/uitest6, uitest7, uitest11 (all PASS lines, no JS exceptions) and uitest12 ALL OK on 2020 Residential; demo_smoke OK on Residential / Structural / Facades; vctltest ALL OK. Corpus sweep 89/89 (docs/SWEEP.md), speed table docs/SPEED.md (sweep timings are inflated by shared remote-host: 2026 Site 48.7 s sweep vs 12.5 s alone).

## 2026-10-16 c5-vctl (takeover from c2-vctl)
* Read handoff, merged master into vctl (fast-forward, only tools/docs changed since 894a4ae: no viewer code delta, so the last vctltest/smoke results stand). c5-annot's parts, element props, anchor and host keys are already consumed by web/viewctl.js (part tree, typeName/levelName/hostId picking).
* Open: 3D/drafting/legend views, tagged-element anchor scaling about `host` centre, Revit-export visual diff via c5-qa.
* d85457d (tag symbol scaling) and ca51db6 (drafting/legend views) merged in master. Merged master back into vctl.
* Finding: no cached scene on disk carries the `host` key yet (Residential plan 180203 has 32 anchored prims, none with host), so the tag-scaling path is untested on real data. After c5-sheets release 8, re-warm Structural/Residential/Commercial scenes (tools/vc_warm.sh, remote-host) and re-run vctltest on Structural L2.
* 3D views: scenes are served (3751 prims for a camera 3D view) but placement semantics are undecided; not started.
* 2026-10-16 20:05: Structural re-warmed on remote-host (release 13 code, 41 scenes, 12 carry host keys); vctltest ALL OK on Structural 124186 (VC_RERENDER=0). Residential/Commercial not re-warmed (older scenes still served, stale fallback).
* Residential re-warmed (17 scenes, release 13 code), vctltest ALL OK on plan 180203. Commercial not re-warmed.
* Commercial re-warmed (20 scenes), vctltest ALL OK on plan 193216. All three demo files now carry release 13 scenes.

## 2026-10-17 c3-vctl (takeover from c5-vctl)
* Read handoff, merged master into vctl. vctltest ALL OK on Residential 180203 after the merge.
* 3D views: decided NOT to overlay. A 3D view scene (Residential {3D} 157966) holds only projected model linework (family symbolic lines, projection/surface_fill segs), no tags, text, dimensions or datums; overlaying it would duplicate the real 3D model. Not selectable in the panel by design.
* Panel layout: rows wrap and the panel no longer scrolls horizontally at 1280 px.
* legend view tested (Commercial 206449): fixed dark/striped paper look (caps + level planes hidden), deef646
* tools/vcalign.py (new): places the view datum linework with the overlay matrix and compares with the viewer's own reader grids: Structural L2 124186, 15/15 grids matched, offsets 0.00 mm (placement/orientation/units exact). Residential has no grids.
* vcalign.py also checks section views (grids parallel to the view direction appear at the right u): Structural Cross Section 582397, East 201907, Longitudinal 579975, North 201922 all PASS (0.00 mm). One oblique grid (elem 598948, diagonal grid in 579975) is drawn at x=21.56 while the extended native line crosses the view plane at x=23.35 and its segment ends at z=15.71 (view plane z=21.55): possible sheets-side question for c3-annot (check against Revit DXF of 579975 if it exists).
* c3-annot answered: Revit omits the diagonal grid 598948 in 579975 (plane not perpendicular); fixed on branch annot. Scenes of Structural need a re-warm (tools/vc_warm.sh) once that fix is merged into rvt-sheets main.
* 2026-10-17 re-warmed all three demo files with sheets release 16 (Structural 41, Residential 17, Commercial 20 scenes), vctltest ALL OK on Structural 124186, Residential 180203, Commercial 193216 (VC_RERENDER=0). Diagonal grid 598948 still drawn: annot fix not yet in rvt-sheets main; re-warm Structural after it lands.
* Structural re-warmed with annot perpendicular-datum fix (sheets e31c92f+): 579975 now 8 grids, all 0.00 mm, the diagonal grid 598948 is gone; vctltest ALL OK on 124186.
* tools/vcsweep.py (new): opens every drawable view (plan/section/drafting/legend) in the overlay and reports prims, segs, texts, JS exceptions. SWEEP OK: Structural 47 views, Residential, Commercial (all cached scenes, 0.0-9.7 s per view).
* Visual check of the paper-look overlay (Residential first floor 180203, headless top-down shot) against Revit's own PNG export: layout, wall cuts, door swings, plants, callout heads A-4 with their numbers, area label, UP stair labels, text size and position all match. Only visible difference: the floor hatch shows horizontal lines clearly but the vertical lines of the crosshatch are faint at 14x zoom (pattern data comes from rvt-sheets).
* re-warmed all three demo files again with sheets cb53624 (Residential 17, Commercial 20, Structural 41 scenes); vctltest ALL OK and vcsweep OK on each.
* Facades 2026 (demo file 3) warmed with sheets cb53624 (22 scenes); vcsweep OK, vctltest ALL OK on plan 873465. All four demo files (Residential, Commercial, Structural, Facades) now have current scenes.
* 24bedb5: header button moved so it is visible in narrow windows; vcui.py real-input test added.
* 2026 Structural (55_Snowdon) warmed (41 scenes) and swept: vcsweep OK, no JS exceptions (first check of a Revit 2026 Structural file in the overlay).
* demo_smoke OK on vctl head for Residential, Structural 2024, Facades 2026 (all three demo files), 2026-10-17.
* URL preset link checked: /?vc=180203&vcp=NAME#model opens the view with the saved preset (textSize 2, lineScale 1.5 applied; test preset removed afterwards).
* aa172a5: Arial Narrow texts (fonts Arial Narrow bold italic: 2184 prims in the corpus scenes, Trebuchet MS and Arial are installed, ARchitxt falls back to Arial) drawn with a 0.82 horizontal squeeze instead of full-width Arial.
* Revit 2017 rst_basic warmed (20 scenes) and swept: vcsweep OK, no JS exceptions (year coverage: 2017, 2020, 2024, 2026).
* re-warmed the four demo files with rvt-sheets 0070540 (Residential 17, Commercial 20, Structural 41, Facades 22 scenes); vctltest ALL OK and vcsweep OK on each. Older caches (2017, Structural 2026) are stale (served with the redraw button).
* 2026-10-17 (c5-viewer): after merging vctl 4a122ba..1a48e76 and the Rust smooth_part hook: uitest6 / 7 / 12 ALL OK, uitest11 all PASS, demo_smoke x3 OK on master a17687b.
* Cold re-render timing (uncached annotation scale, remote-host capped): Residential plan 180203 1:37 2.4 s (first, includes worker start), 1:61 0.44 s; Structural L1 124186 1:37 4.6 s, 1:61 0.86 s. Fine for a live demo.
* Writer output (write-lab generated/full/full_fin_2024.rte, 11 plans + 4 sections) opens in the overlay: scenes render live (no warm needed for a small file), vcsweep OK, no JS exceptions.
* re-warmed the four demo files with rvt-sheets 86a805b (patterns.hatch guard); vctltest ALL OK and vcsweep OK on each. One h1run pull of four dirs hit a broken pipe; pulling the dirs one at a time worked.
* re-warmed the four demo files with rvt-sheets bf4ddfa (visibility lists); vctltest ALL OK and vcsweep OK on each. h1run pull of several dirs in one call breaks the pipe: pull one dir per call with a retry.
* rvt-sheets schedule.py commits (2477c2b etc.) do not stale the view scenes: Residential 180203 still X-Vc-Stale 0 after them, no re-warm needed.
* vstyletest.py runs against the real window.vstyle with VS_MOCK=0 (c3-viewer branch vstyle 19cf038+): ALL OK (default hiddenline with full opts, per-view autosave and restore, preset style). Residential plan 180203 overlay on top of the hidden-line 3D looks like the Revit plan (screenshot checked).

## c1-hl (hidden line 3D style), branch hl
* web/hl.js (new) + patches in web/app.js (shader uniforms uStyle/tOvr/uPassT, pick hides edges, events): styles Hidden Line (default), Shaded, Consistent Colors, Realistic (old default), Wireframe; select in the header, ?style=NAME, remembered in localStorage.
* Edges: worker extracts sharp edges (>30 deg), element boundaries, open edges; smooth edges (2..30 deg) are silhouette candidates decided per frame in the vertex shader. Thick lines by 2 extra offset passes. Snowdon structural: 575k edges in 2.4 s. Models > 12M triangles open in Realistic until the user picks Hidden Line.
* Faces: white unlit with polygonOffset, translucent elements (floors, transparency %) in a second pass (mesh twin) so edges behind them fade like Revit.
* Resolved view graphics: rvtviewer/vg3d.py + vg3d_worker.py (GET /api/m/{mid}/vg3d/{viewId}, rvt-sheets resolve_view: filter/category overrides, fills, transparency, line colour/weight, hidden elements); applied when a view is opened (or window.__hl.loadView({id})).
* Level outlines / grids drawn as dashed lines (levels black, grids magenta) in hidden-line, labels black on white.
* Measured: tools/hl_score.py (registered line F1 vs Revit export). Snowdon Structural 'Structure Only' (600158): F1 0.885 (precision 0.86, recall 0.92); first version 0.74.
* tools: shot3d.py --style hidden|shaded|consistent|wire|realistic --vg VIEWID (shots default to realistic), style_test.py (round trip, JS errors).
* Open: surface patterns (hatch) on faces, halftone, yellow framing fills need the sheets filter evaluator (Z Offset filters match 6 of the beams Revit colours), annotation categories in 3D, edge cache.
* DEMO NOTE: with hidden line as default the first demo step (materials/textures house) must pick Realistic in the Style select; merge decision with c3-viewer / orchestrator.
* 2026-10-18: Snowdon structural 3D views (13), registered line F1 (tools/hl_table.py): mean 0.66; category views 0.78-0.99 (Framing 0.99, Slabs 0.96, Columns 0.87, Walls 0.78, Foundations 0.80, Structure Only 0.90), FlatColors / section-box views score low (Revit draws filled cut faces and flat shading there, not hidden line). review_shots had a wrong column for the perspective flag (fixed: ortho cameras are now used). Needs the view display style from the reader (NEEDS-FROM-READER.md).
* Edge worker stress (node, synthetic wavy grid): 0.98M tris -> 1.29M edges in 0.7 s (342 MB RSS); 3.9M tris -> 5.1M edges in 2.9 s (1.15 GB RSS). Edge vertex = 26 bytes (int8 normals), Snowdon F1 unchanged (0.900). remote-host has no chromium, so big-model browser tests stay on remote-host (3 GB cap).
* 23_rme_advanced (118 MB glb, 48 meshes) opens in hidden line under a 3 GB cap: 1.2M edges, 7-43 s edge build (worker, progressive). Edges shorter than 2 cm (?minedge=M, H.minEdge) and sliver-adjacent edges are dropped (-27% edges). Known artifact: a translucent block on that model still shows scattered 1-3 px specks inside its faces (not a depth-offset issue: tested offsets 0.5..6); suspect interior geometry of the translucent mass seen through, to investigate.
* 2024_writer_house1 Review Iso: geometry matches Revit visually but the registered line F1 is 0.34 because Revit's export includes long dashed level lines with labels (extents far larger than the house) that the registration and recall count; hl_score cannot separate them (a density filter removed the house instead). Compare these files with levels in both (shot3d --levels) or crop Revit's image by hand.
* vg: sheets dev has the vg.json route (67a24e0), sheets master does not; my four-file re-warm used master code (scenes fresh, X-Vc-Stale 0). Re-warm again when dev is promoted to master.
* vg.json is in sheets master (merge of branch vg): /api/m/{mid}/vc/vg/{vid} returns 200 for the four demo files; real end-to-end pick on Structural L1 shows the V/G block (view template Structural Framing Plan). Scenes still X-Vc-Stale 0, no re-warm needed.
* 2026-10-17: after c3-viewer camera fix (91ee8c3, views looked along the wrong direction) vcalign on Structural sections 582397/201907/579975/201922 still PASS (placement is independent of the camera); section North overlay renders in the right place over the model. remote-host rule from the user: heavy tests only on remote-host from now on.
* remote-host rule: remote-host has no chromium, so browser tests (vctltest/vcsweep/vcalign/vcui/vstyletest) cannot move there. They stay on remote-host as single-view Residential-size checks (MemoryMax 1.5G, one at a time); sweeps over many views and Structural/Facades-size runs are paused until remote-host has a browser (decision for the user: install chromium on remote-host, or accept remote-host for single-view checks).
* re-warmed Residential 17, Commercial 20, Structural 41 scenes with sheets 01cddd3 (bricks/schedule merge); Facades queued (remote-host MemAvailable 9.4 GB when tried). No browser tests run (remote-host rule).
* Facades re-warmed (sheets 01cddd3): all four demo files current.
* 2026-10-18: single-view check on remote-host (Residential 180203, server + test each capped at 1.5 GB): X-Vc-Stale 0, vctltest ALL OK on the re-warmed (sheets 01cddd3) scenes. Server stopped.
* vstyle opts (docs/VSTYLE-API.md) now implemented in hl.js: edgeAngle (re-extracts edges), silhouettes, hiddenLines off|faint|dashed (second edge pass with GreaterDepth, grey / stippled), lineWeight multiplier, transparency, halftone, faceColor. NOTE: default hiddenLines is 'off' (Revit's hidden line look), the draft doc says 'faint'. tools/vstyle_opts_test.py cycles the options on house1 (needs RVT_VIEW).
* Edge cache: extraction results go to IndexedDB (key: model id, build stamp, mesh, edge angle, min edge); Snowdon rebuild 2112 ms -> 208 ms (tools/hl_cache_test.py). Default minimum conditional edge 1 cm (2 cm cost 1% F1: 0.900 -> 0.891).
* Material graphics (surface/cut pattern + colour per material) requested from the reader: Revit paints a material's surface pattern colour in hidden line (the grey interior walls of house1).
* f1012fb: style options row in the panel.
* hl_score: removes long sparse dashed chains (levels/grids) from Revit's image before registering; hl_table reads __ours3d_hl.png and _hl2.png. Writer scenes (Review Iso) score 0.13-0.61 (house1 0.61, tower20 0.30, office7 0.13, campus4 0.20): geometry matches but Revit draws 20+ L-shaped level lines with bubbles around the models and our render has none, and the tower20 top: Revit shows a closed top slab with a core box, ours is open (no top floor in our geometry: reader/writer question, not hidden line). Default floor transparency removed (floors opaque unless the view's overrides say otherwise).
* Levels in 3D hidden line now follow the datum plane envelope (GET /api/m/{mid}/datums3d, rvtviewer/datums3d_worker.py via rvt-sheets File: origin, in-plane axes, envelope): dashed lines along the envelope, only the two edges at the corner farthest from the eye are drawn (Revit's L, recomputed per camera change). Rule inferred from two Revit exports (house1 SE camera -> NW apex, Snowdon SW camera -> NE apex); not yet verified on a third. Still open: bubbles/heads with name + elevation at the arm ends, grids (none in these files), per-view extents (ExtentElem m_freeEnd3d / bubble ends).
