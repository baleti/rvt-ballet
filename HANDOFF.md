# HANDOFF (rvt-viewer, c4-viewer) - 2026-10-15

State: master clean, tag demo-ready = 91eae28 (smoke OK Residential / Structural / Facades, models prepared for this converter).
Done this session: plan/section/elevation views framed + clipped to stored crop; plan view depth (shader discard uBot); 3D views clip to stored section box; smooth vertex normals (35 deg crease, RVT_SMOOTH=0 disables); Revit navigation (Shift+middle orbit, middle pan, wheel zoom at cursor, dbl middle fit, Alt+left / Alt+Shift+left touchpad fallbacks, right button inert; tools/uitest12.py); rosetta oracle table in docs/SHOWCASE.md (tools/rosetta_dev.py, compare_gt area ratio).
Background: ~/scratchpad q.sh retry loop queues remote-host job vsweep4 (full 78-file re-sweep, RVT_SWEEP_REDO=1) as soon as remote-host MemAvailable >= 11 GB; when done: h1run pull .cache/rvt-viewer/sweep.jsonl, tools/sweep_table.py, tools/demo_table.py, update DEMO.md table.
Next: sweep table in DEMO.md; Rust fast path items (NEEDS 12/13/10), material browser polish, per-class fidelity buckets, writer scenes (~/rvt-research/write-lab/scenes) vs Revit: tell c4-writer if we draw what Revit cannot.
Tests: tools/uitest6/7/11/12.py MODELDIR PORT OUT (PORT 4-digit!), tools/demo_smoke.sh FILE PORT.

## c5-viewer start (2026-10-15)
Baseline smoke OK (2020 Residential). Rust fast path + preimport thread already adopted. Task B nav done earlier. Queue loop tools/queue_vsweep.sh running (log ~/.cache/q_vsweep.log) to start remote-host vsweep4; then pull sweep.jsonl, tools/sweep_table.py, update DEMO.md.
19:03:48 vsweep4 started on remote-host after reboot (h1run tail vsweep4); then pull .cache/rvt-viewer/sweep.jsonl, tools/sweep_table.py, update DEMO.md
