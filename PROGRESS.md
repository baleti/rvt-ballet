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
