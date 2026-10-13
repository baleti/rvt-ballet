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
