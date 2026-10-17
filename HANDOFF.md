# HANDOFF (rvt-viewer, c4-viewer) - 2026-10-15

State: master clean, tag demo-ready = 91eae28 (smoke OK Residential / Structural / Facades, models prepared for this converter).
Done this session: plan/section/elevation views framed + clipped to stored crop; plan view depth (shader discard uBot); 3D views clip to stored section box; smooth vertex normals (35 deg crease, RVT_SMOOTH=0 disables); Revit navigation (Shift+middle orbit, middle pan, wheel zoom at cursor, dbl middle fit, Alt+left / Alt+Shift+left touchpad fallbacks, right button inert; tools/uitest12.py); rosetta oracle table in docs/SHOWCASE.md (tools/rosetta_dev.py, compare_gt area ratio).
Background: ~/scratchpad q.sh retry loop queues remote-host job vsweep4 (full 78-file re-sweep, RVT_SWEEP_REDO=1) as soon as remote-host MemAvailable >= 11 GB; when done: h1run pull .cache/rvt-viewer/sweep.jsonl, tools/sweep_table.py, tools/demo_table.py, update DEMO.md table.
Next: sweep table in DEMO.md; Rust fast path items (NEEDS 12/13/10), material browser polish, per-class fidelity buckets, writer scenes (~/rvt-research/write-lab/scenes) vs Revit: tell c4-writer if we draw what Revit cannot.
Tests: tools/uitest6/7/11/12.py MODELDIR PORT OUT (PORT 4-digit!), tools/demo_smoke.sh FILE PORT.

## c5-viewer start (2026-10-15)
Baseline smoke OK (2020 Residential). Rust fast path + preimport thread already adopted. Task B nav done earlier. Queue loop tools/queue_vsweep.sh running (log ~/.cache/q_vsweep.log) to start remote-host vsweep4; then pull sweep.jsonl, tools/sweep_table.py, update DEMO.md.
19:03:48 vsweep4 started on remote-host after reboot (h1run tail vsweep4); then pull .cache/rvt-viewer/sweep.jsonl, tools/sweep_table.py, update DEMO.md
19:38:03 master=071285d (vctl v1 merged, .venv untracked and rebuilt, GLB byte-identical, 3-file smoke OK), demo-ready moved here
23:53:16 master 515bfe9: vctl 0c6ab1d merged (vctltest ALL OK), corpus table 89/89 (DEMO.md, SWEEP.md), docs/FIDELITY-FINAL.md, 3 demo models re-prepared with the new reader (sheets warm for Structural/Facades needs remote-host >= 11 GB: rvt-view --prepare with RVT_WARM_NO_LOCAL=1), demo-ready moved.
01:44:14 demo-ready -> e1d81e7 (3-file smoke OK, sheets warm done, inspector class accuracy line)
01:47:13 vctl d2ee7ef merged, demo-ready moved (3-file smoke + vctltest OK)
02:36:42 vctl 3fc4fcd merged (docs), smoke OK, demo-ready moved
04:51:30 vctl 7011f97 merged, 3-file smoke + vctltest, demo-ready moved
05:39:06 vctl 34c4018 merged (3-file smoke + vctltest OK), demo-ready moved
06:01:29 vctl 5d3458a merged; vctltest ALL OK on Structural L2 (VC_RERENDER=0, 1.8 GB worker) and Residential; smoke OK; demo-ready moved
06:13:06 demo models re-prepared after reader change (face->edge index); smoke OK; sheets warm retry loop tools/queue_warm.sh running (log ~/.cache/q_warm.log)
09:51:32 sheets warm for Structural/Facades done (08:34), 3-file smoke OK, sweep6 89/89, demo-ready on 52b8ed8. Open: reader stage of 2017-19 MEP, MEP geometry 24-37 s (NEEDS-FROM-READER 20), item 21 writer scenes approx jump.
14:17:05 vctl 894a4ae merged (Paper look), smoke x3 + vctltest OK, demo-ready moved; osweep (oracle_sweep.py) running on remote-host
16:29:49 vctl d85457d merged (tags scale about own point), smoke x3 + vctltest OK, demo-ready moved
16:39:12 vctl 9a1da21 merged (drafting/legend views), smoke x3 + vctltest OK, demo-ready moved
17:22:59 vctl 5ae62b1 merged, smoke x3 + vctltest OK, demo-ready moved
00:58:06 vctl 940d633 merged (panel CSS), smoke x3 + vctltest OK, demo-ready moved
01:08:33 rust smooth_part + progress-file hook adopted (RVT_NO_RUST_SMOOTH=1 disables), Residential GLB identical, conversion 5.1 -> 2.9 s, smoke x3 OK, demo-ready moved
01:11:14 vctl deef646 merged (legend paper look), smoke x3 + vctltest + uitest12 OK, demo-ready moved
