# HANDOFF (rvt-viewer, c2-viewer) - updated 2026-10-15 (usage limit)

Older notes: HANDOFF-c4-viewer.md. Progress log: PROGRESS.md (2026-10-15 section).

## State
* master clean, tag `demo-ready` = 3c46555 (smoke OK on Residential / Structural / Facades; models prepared for that commit; later commits are docs + tools/perftest/cdp only).
* Sheets caches go stale on every reader stamp change. Background retry loops (may have ended with the session) warm Structural + Facades + Residential sheets on remote-host: re-run `~/src/rvt-sheets/rvt-sheets warm FILE --remote-host` if `/sheets/api/<mid>/cache.json` says cached:false.
* remote-host jobs queued by retry loops (check `h1run status`): `vsweep3` (full re-sweep -> `h1run pull .cache/rvt-viewer/sweep.jsonl`, `tools/sweep_table.py`, `tools/demo_table.py`), `vperf` (converts 2023 rme_basic + 2019 Arch_Link into ~/.cache/rvt-viewer/perf/ -> pull, then `tools/perftest.py DIR PORT vulkan` = real Iris Xe headless, no window).

## NEXT (in order)
1. PRISM TEXTURES (big visible fidelity gap, 2026 Facades): bricks / stained wood / quartz render white. In rvtviewer/materials.py `asset_extras.tex()`, the colour-map test `nm.endswith(('diffuse','_color','_colour'))` misses Prism `opaque_albedo` (bitmap e.g. 1/Mats/brick_running_color_grey.jpg, present in ~/.cache/rvt-textures). Treat `opaque_albedo` like generic_diffuse (return at once); NOT surface_albedo (reflectance). Prism scales have m_unit None: values are INCHES (brick 32 x 30 -> 12 courses in the 256 px image), so unit None + Prism -> 1/12 ft. Then the white rgb (placeholder) must take the swatch mean / shading colour (same rule as generic bitmap diffuse). Re-prepare demo, smoke, tag.
2. Perf numbers into README (Structural 665k tris 16.6 ms/frame synced, +10 ms on shadow redraw, caps 12 ms; Facades 7.5 ms; heavy files from vperf).
3. Brief leftovers: views fidelity vs Revit, wall/stair polish.
