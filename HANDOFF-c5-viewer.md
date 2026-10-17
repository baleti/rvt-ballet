# HANDOFF c5-viewer (claude5 -> claude3, 2026-10-17)

## State
* master 70877da, clean; tag `demo-ready` = 05a248b (3 demo files smoke-tested: Residential 2020, Structural 2024, Facades 2026; the later commits are notes only). Branch `vctl` (worktree ~/src/rvt-viewer-vctl, owner c2/c3-vctl) is fully merged into master; merge new vctl commits with: git merge vctl, then tools/demo_smoke.sh on the 3 files, tools/vctltest.py URL 180203 on Residential, uitest12 if app.js changed, then `git tag -f demo-ready`.
* `.venv` is a real untracked directory (cadquery-ocp mapbox-earcut shapely numba): never let a branch track it (it was replaced by a symlink once).
* No h1run job of mine is running; no retry loops. (h1-par26 on remote-host is c5-geometry's.) Demo caches are warm (models + sheets) for the three files; the reader changes often: re-prepare before the interview: `RVT_WARM_NO_LOCAL=1 bin/rvt-view --prepare <3 files>` (sheets warm falls to remote-host when it has >= 11 GB, else `tools/queue_warm.sh` retries).
* Demo command: bin/rvt-view FILE [--sheets] [--hide Planting,Entourage]. DEMO.md has the script and the 89/89 corpus table.

## Done this session (all committed)
Task B navigation re-verified (uitest12). Corpus sweeps: 89/89 pass (DEMO.md, docs/SWEEP.md), speed table docs/SPEED.md (first usable 4.5-7 s on 2024+ Structural/Facades/Electrical; MEP 2017-2023 still 12-23 s), fidelity tables docs/FIDELITY-FINAL.md + FIDELITY-2017-2019.md, inspector line "reader accuracy for <class>" (web/fidclass.json via tools/fid_table_md.py). Viewer vs Revit oracle: tools/oracle_sweep.py, docs/ORACLE-SWEEP.md (248 files, per class), tools/oracle_bad.py, tools/vol_probe.py, tools/compare_gt.py (oriented volume; duplicate gt solids counted once; open meshes skipped). Rust hooks adopted: smooth_part (RVT_NO_RUST_SMOOTH=1 disables), progress-file read. `refined_volume` IndexError fixed (build.topology_check skips deduped elements). rvt-view --hide. materials.write_images faster. vctl (annotations/view control) v1.. merged repeatedly.

## Parity numbers (viewer mesh vs Revit gt, docs/ORACLE-SWEEP.md)
FamilyInstance volume within 2 %: 86 % (within 10 %: 89 %); SWall 98 %; Floor / Ceiling / RoomElem / ProfileRoof / MEP curves 100 %. Weak: BaseRailing (IoU 0.57, host bbox includes children), TopRail vol 33 %, Rebar IoU 63 %, AnalyticalModelColumn 67 %.
Open reader findings I filed in NEEDS-FROM-READER.md (no reply yet), these are the remaining real defects:
1. Item 22: Lighting Fixtures (195 in 2020 rme_basic/advanced): reader mesh has an extra nested body 1000100000 (1120 tris, 1 face, volume 3.25) that Revit's Fine solid does not contain (body 100000 = Revit's solid exactly). Reader should drop hidden nested nodes.
2. Item 23: complex rosettas: 50 of 70 exact; `fam_sweep_spline_path` (two Hermite side faces tessellated with 10x area: spurious sheet, screenshot ana_c5/viewer_sweep_spline_path_base.png), `fam_blend_twist` (twisted ruled faces are 2 flat triangles, volume +17..26 %), `fam_blend_rect_circle` (0.90), `dbg_sweep` (1.09), `fam_sketch_profile_spline` / `fam_sweptblend` (open meshes).
3. Speed: MEP geometry stage 24-37 s, 2017-2019 MEP cold extraction (item 20; 2017 rme_advanced now reader 7 s warm / 19 s cold, total 45 s).
4. Writer scenes (item 21): 20-59 % box-only, 2026 output reads `approx` more than 2024.

## Next steps (suggested)
* Answer replies in NEEDS-FROM-READER.md from c5-geometry; re-run `tools/oracle_sweep.py run` on remote-host after a reader change (move ~/.cache/rvt-viewer/oracle_sweep.jsonl aside first; the rosetta .rte files must exist on remote-host: rsync ~/rvt-research/rosetta remote-host:rvt-research/rosetta/), then `tools/oracle_sweep.py table`.
* If the reader does not drop hidden nested bodies, a viewer-side filter (nid 1000100000, 1-face body) would be a hack: prefer the reader fix.
* Keep demo caches fresh; before the interview run --prepare and the 3 smoke tests.
* Material browser, wall joins/openings, section/measure polish: no known defects; screenshots of Residential / Structural / Facades looked right.

## Conventions
No em dashes; remote-host light (one capped job, MemoryMax 2G), heavy on remote-host via h1run when MemAvailable >= 11 GB (queue lines in ~/demo-state/H1-QUEUE.md); never touch the user's workspace except 178; tests: tools/uitest6|7|11|12.py MODELDIR PORT OUT (MODELDIR = one model's cache dir), tools/vctltest.py, tools/demo_smoke.sh FILE PORT.
