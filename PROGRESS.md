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
