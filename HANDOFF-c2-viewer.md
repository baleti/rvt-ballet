# HANDOFF c2-viewer (session-limit stop, 2026-10-15)

## State
* master clean and tested; tag `demo-ready` = 3f31418 (smoke OK on Residential / Structural / Facades, models prepared for this converter version). Demo: `~/src/rvt-viewer/bin/rvt-view /full/path/FILE.rvt --sheets`, script in DEMO.md.
* Done today (PROGRESS.md 2026-10-15): reader final accuracy table in README, section caps (poche) for sections / plans, sun shadows, bump maps, Prism textures (Facades brick/wood/quartz/copper), CategoryElem z-fight fix, grids 1-8 fix, plan view polish, Fit to visible, sweep 121/121 (all 78 corpus files < 0.5% box-only), real-GPU frame times in README.
* Background (may still run): a retry loop warming Structural + Facades sheets on remote-host (`rvt-sheets warm FILE --remote-host`). No viewer h1run jobs running (vsweep3, vperf done and pulled).
* c2-sheets just answered (end of ~/src/rvt-sheets/HOOKS.md): sheets now fall back to an older complete cache after reader changes (cache.json has stale/current_key). NOT yet verified from the viewer side.

## Next
1. Verify the sheets stale fallback: `bin/rvt-view FILE --no-browser --port N`, `curl localhost:N/sheets/api/<mid>/cache.json` for Structural/Facades (expect cached true, stale true); if the badge should say "stale", wire it in web/app.js (updateCachedBadge).
2. Plan views: frame on the view's extent (`m_extentElemId`, view range `m_pPlanViewRange2` offsets are in the DBViewPlan record) instead of the whole model; consider view depth clipping.
3. Brief leftovers: views fidelity vs Revit, wall/stair polish.

## Restart / checks
* Tests: `sh tests/run.sh MODELDIR`, `tools/uitest6.py|uitest7.py|uitest11.py MODELDIR PORT OUT`, `tools/uitest10.py FILE --sheets --port N`, `tools/demo_smoke.sh FILE PORT`.
* Demo prep after converter/reader changes: `RVT_WARM_NO_LOCAL=1 bin/rvt-view --prepare <3 demo files>`, smoke, then `git tag -f demo-ready`.
* Perf on the real GPU without a window: `tools/perftest.py MODELDIR PORT vulkan`.
* Sweeps only on remote-host (`h1run run vsweepN ... python tools/sweep.py FILES`), never on remote-host.
