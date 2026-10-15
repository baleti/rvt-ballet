# HANDOFF c4b-viewer (claude4 ending, 2026-10-15)

## State
* master clean and tested; tag `demo-ready` = 91eae28 (smoke OK on Residential / Structural / Facades; the three models were prepared with this converter). Later commit(s) are HANDOFF files only.
* Done: views framed + clipped to the stored crop region (datums.py `_crop`, app.js `cropFrame`), plan view depth (`U.uBot` shader discard, not a clip plane: a clip plane breaks the section-cap stencil parity), 3D views clip to their stored section box, smooth vertex normals (build.py `smooth_part`, 35 deg crease, `RVT_SMOOTH=0` disables; app.js flips the normal toward the flat screen-space normal per fragment because reader winding is inconsistent), Revit navigation (Shift+middle orbit, middle pan, wheel zoom at cursor, double middle-click fits, Alt+left / Alt+Shift+left touchpad fallbacks, right button inert), rosetta-vs-Revit table in docs/SHOWCASE.md (tools/rosetta_dev.py, compare_gt.py now also gives an area ratio).
* Bugs A-D: not mine (no such list reached this session).

## Running h1run jobs
* None started. A retry loop (tools/queue_vsweep.sh, background shell of the old session, probably dead) was waiting for remote-host MemAvailable >= 11 GB (it was 8-9 GB) to queue `vsweep4` = full 78-file re-sweep with the new converter. Restart: `nohup tools/queue_vsweep.sh > /tmp/q.log 2>&1 &` (or run the h1run command in it by hand). When done: `h1run pull .cache/rvt-viewer/sweep.jsonl`, `tools/sweep_table.py`, `tools/demo_table.py`, put the pass/fail table in DEMO.md.

## Next steps
1. Full-corpus sweep table in DEMO.md (above); fix failures.
2. Sheets of Structural + Facades: `--prepare` reports "remote-host warm failed" (remote-host memory); caches exist and show cached, re-warm with `~/src/rvt-sheets/rvt-sheets warm FILE --remote-host` when remote-host has room.
3. Writer scenes (~/rvt-research/write-lab/scenes/*.rte, house_lv): render them and tell c4-writer if we draw what Revit cannot (not looked at yet).
4. Geometry-kind badge + compare-with-Revit deviation in the inspector (compare.json now has id, mesh_area, aratio per element); the 2026 sweep showcase shot is framed too wide (fit uses the whole model).
5. Older list: Rust fast-path adoption (NEEDS-FROM-READER 10/12/13), material browser polish, per-class fidelity buckets, 3D-view section-box quirks.

## Checks
* Tests: `tools/uitest6.py|uitest7.py|uitest11.py|uitest12.py MODELDIR PORT OUT` (PORT must be a valid 4-5 digit port), `tools/demo_smoke.sh FILE PORT`. Use `.venv/bin/python` for anything that converts (system python lacks mapbox_earcut: boxes instead of meshes).
* After converter/reader changes: `RVT_WARM_NO_LOCAL=1 bin/rvt-view --prepare <3 demo files>`, smoke, `git tag -f demo-ready`.
