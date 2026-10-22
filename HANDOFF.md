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
02:36:37 vctl 4ccad68 merged (vcsweep), smoke x3 OK, demo-ready moved
05:54:09 vctl 4a122ba merged (narrow-window button, tabs wrap, Arial Narrow width), smoke x3 + vctltest + uitest12 OK, demo-ready moved
07:55:21 demo models re-prepared (reader changed again), smoke x3 OK; queue_warm.sh retrying the sheets warm of Structural/Facades on remote-host
08:30:13 all demo caches + sheets warm, smoke x3 OK, demo-ready on 05a248b

## c6-viewer state (2026-10-19)
Master has: Revit navigation, hidden-line default with surface-pattern hatch (web/app.js fragment shader + materials.js rows 6..9), parallel-projection views (orthoLook, view bar button, tools/uitest13.py), section far clip (datums.py views[].depth from Viewer m_boundedSpace z far bound; app.js clips beyond it). Tests that pass on 2020 Residential (remote-host, 2 GB cap, one at a time): demo_smoke.sh, uitest6, uitest12, uitest13. Pending: demo_smoke on Snowdon / Facades (vsmoke7) and tools/hl_score.py of the Residential building section (hlscore1), both queued in ~/demo-state/H1-QUEUE.md (remote-host gate blocked by its VMs, known). Models converted before 2026-10-18 lack surface patterns / depth until re-converted or `rvt-view --prepare` is re-run. Open ideas: cut-pattern hatch on section caps, drafting patterns in 3D, honour far_clipping / crop_active through rvt_viewdisp.view_clip.

## c7-viewer state (2026-10-20)
master 78e5ad0, demo-ready 0e898a3 (smoke: Residential remote-host, Snowdon Structural + Facades remote-host via tools/queue_vsmoke7.sh + tools/h1_venv.sh; uitest6/12/13 ALL OK on Residential).
Done: hidden-line section cut outline + white cut faces + terrain ground line (app.js cutSegments / outlineLines, F1 0.468 -> 0.676 vs Revit building section, tools/hl_score.py); parameter table adopted (docs/PARAMETERS.md, inspector note); shot3d --isolate / stale banner hidden; tools/prune_cache.py (dry run, user decides --delete).
Open: roof gable of Residential 158021 missing = reader mesh (NEEDS-FROM-READER item 25); poche / cut patterns on caps (needs per-element stencil); Snowdon elevation 4969 hidden-line check; after any rvtviewer/*.py change run `rvt-view --prepare` on the 3 demo files. remote-host shots: tools/capped.sh + RVT_MEM_CAP=2G ALLOW_remote-host=1, uitests take a converted cache dir as MODELDIR (not a folder of .rvt).

## c8-vctl state (2026-10-20)
vctl head has master merged + enrichTypes (viewctl.js); merge request for c8-viewer in VCTL-HOOKS.md (1fe1edd). Verified on remote-host (Residential 180203, capped): demo_smoke, vctltest, vcui, vcsweep ALL OK. remote-host job vcb-fac (tools/h1_vctl_browser.sh Facades 614119) started to browser-check a big file; the view id may not exist (cache scene gone): check h1run tail vcb-fac and pick a real plan id from /api/m/MID/vc/views if it fails.
Open: 3D views carry no annotation overlay (no data), keynote tags absent from all cached scenes, angular/radial dims depend on sheets.

## c8-viewer state (2026-10-21)
master; demo-ready = adfdbc3 (all three demo models prepared on remote-host with the current stamp, sheets warmed on remote-host, demo_smoke OK on all three from the remote-host caches; sweep7 89/89 ok on remote-host; uitest6/12/13 ALL OK; 33 node tests). IMPORTANT: any rvtviewer/*.py edit changes viewer_stamp: re-run rvt-view --prepare on the three demo files (RVT_WARM_NO_LOCAL=1 RVT_MEM_CAP=3500M ALLOW_remote-host=1 tools/capped.sh, then tools/queue_warm2.sh for the sheets warm) before moving demo-ready.
Done this session: silhouettes flag fix (viewctl.js vsFromView: display.silhouettes is a line-style override, not off; piles/columns outlines back, Snowdon South elevation F1 0.195 -> 0.635), cut-pattern hatch on hidden-line section caps + earth poche under terrain (app.js updateCaps / soilPoche, web/cutpattern.js from codex), view-scale patterns, no-crop section framing = model extents, vctl merges (1fe1edd, 4abc0dd), hl_score_fast.py.
Open: reader items 25 (roof gable mesh) and 26 (Earth pattern grid angles) in NEEDS-FROM-READER.md; hatch lowers the pixel F1 (0.68 -> 0.60) because patterns differ from Revit's; Longitudinal needs a hidden-line Revit export to score; framing at openView depends on the viewport aspect at that moment (shot tool artefact?); Plumbing first usable 11.8 s (reader).
Smoke recipe: tools/queue_vsmokeN.sh (copy of queue_vsmoke7.sh with a new job name) then tag demo-ready.

Also done 2026-10-21/22: cut patterns up to 64 grids + soil poche + elevation family (views[].family), framing fixes, codex modules cutpattern/viewframe/soilquads/cropextent (tests/js, 33 tests), docs/HIDDEN-LINE.md section, DEMO.md MEP note (RVT_NOFAST=1 for MEP-heavy 2024+), SCOREBOARD.md section. Open: reader items 25 (roof gable mesh), Rust MEP parity (c8-geometry note), Revit omits a toilet/sink our section draws (cause unknown), Longitudinal needs a hidden-line Revit export.

## claude8 takeover state (2026-10-22)
master, demo-ready = adfdbc3 (only docs/tools commits since; no rvtviewer/*.py or web change, demo caches valid). Verified: Residential demo_smoke (remote-host), Plumbing 2024 demo_smoke (remote-host, vsmoke14), 33 node tests + 4 python unit tests green. Queue audit: NEEDS 10/12/13, fidelity buckets, 89/89 table, nav, revolve/sweep checks all done. Closed: toilet 152823 (self-consistent on our side, Revit omission unexplained, needs a Revit-side element dump), crop clip already exists. Residential plan hidden-line F1 0.502. Open: reader item 25 (roof gable), Snowdon L2 plan framing (scale 0.78 in hl_score_fast; pair files in ~/review-compare/3d_43_Snowdon_Towers_Sample_Structural, run on remote-host). Any rvtviewer/*.py edit => re-run rvt-view --prepare on the 3 demo files.

## claude8 update 2026-10-22 13:12
Snowdon Structural L2 plan 581543 hidden line scored on remote-host (tools/queue_l2plan.sh): F1 0.586 (P 0.452 R 0.833), registration scale 1.43 (crop off here, Revit export cropped); Revit shows joist lines and no floor fill, ours slab stipple. Diagnostic tools/vis_cats.py (hidden categories of view 581543) queued via tools/queue_viscats.sh but never ran (remote-host gate stuck at 7.7 GB); rerun with tools/queue_viscats.sh (a retry loop may still be running: check pgrep before starting). No viewer code changed; demo-ready still adfdbc3.
