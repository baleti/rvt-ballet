# HANDOFF (rvt-viewer, c2-viewer) - updated 2026-10-15

Older notes: HANDOFF-c4-viewer.md (2026-10-14). Progress log: PROGRESS.md (2026-10-15 section).

## State
* master = demo-verified, tag `demo-ready` = 49f9ed5 (smoke OK on Residential / Structural / Facades, uitest10 --sheets OK, uitest6/7/11 OK). Demo models prepared for that commit.
* Sheets of Structural + Facades: stale after the reader stamp change; a background retry loop runs `rvt-sheets warm ... --remote-host` until remote-host has room (DEMO.md: open Facades without --sheets if the badge says not cached).
* remote-host job queued by retry loop: `vsweep3` (full re-sweep, RVT_SWEEP_REDO=1). When done: `h1run pull .cache/rvt-viewer/sweep.jsonl`, `python3 tools/sweep_table.py`, `python3 tools/demo_table.py`, commit.
* Section caps merged (56891b5). demo-ready = d28ff71.

## Next items
1. Re-sweep tables when vsweep3 has run. 4. Brief items: textures (bump), views fidelity, triangle budget check on real GPU (workspace 178, silent).
