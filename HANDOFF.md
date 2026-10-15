# HANDOFF (rvt-viewer, c2-viewer) - updated 2026-10-15 (usage limit)

Older notes: HANDOFF-c4-viewer.md. Progress log: PROGRESS.md (2026-10-15 section).

## State
* master clean, tag `demo-ready` = 4309949 (smoke OK on Residential / Structural / Facades; models prepared for that commit; later commits are docs + tools/perftest/cdp only).
* Sheets caches go stale on every reader stamp change. Background retry loops (may have ended with the session) warm Structural + Facades + Residential sheets on remote-host: re-run `~/src/rvt-sheets/rvt-sheets warm FILE --remote-host` if `/sheets/api/<mid>/cache.json` says cached:false.
* remote-host jobs queued by retry loops (check `h1run status`): `vsweep3` (full re-sweep -> `h1run pull .cache/rvt-viewer/sweep.jsonl`, `tools/sweep_table.py`, `tools/demo_table.py`), `vperf` (converts 2023 rme_basic + 2019 Arch_Link into ~/.cache/rvt-viewer/perf/ -> pull, then `tools/perftest.py DIR PORT vulkan` = real Iris Xe headless, no window).

## NEXT (in order)
1. Prism textures DONE (6e5bb48). Sweep + perf DONE (README). Sheets of Structural / Facades still stale until remote-host has room (`rvt-sheets warm FILE --remote-host`); request to c2-sheets in rvt-sheets HOOKS.md (serve older complete cache).
2. Brief leftovers: views fidelity vs Revit (plan crop / view range), Prism bump (surface_normal maps), wall/stair polish.
