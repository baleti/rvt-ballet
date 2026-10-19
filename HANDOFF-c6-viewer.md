# c6-viewer handoff (2026-10-19)
State: master clean and committed (hl merged). See the "c6-viewer state" section at the end of HANDOFF.md and PROGRESS.md.
remote-host jobs: none running. Queued (blocked by remote-host memory gate): vsmoke7 (demo_smoke on Snowdon Structural + Facades), hlscore1 (tools/hl_score.py, inputs in ~/review-compare/viewer-shots/), both in ~/demo-state/H1-QUEUE.md.
Next steps: run those two when remote-host has 11 GB; re-run `rvt-view --prepare` on demo files before an interview (viewer code changed the cache stamp); open ideas: cut-pattern hatch on section caps, drafting patterns in 3D, use rvt_viewdisp.view_clip (far_clipping / crop_active).
