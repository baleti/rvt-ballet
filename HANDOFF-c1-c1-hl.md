# HANDOFF c1-hl (hidden line 3D style), branch hl, worktree ~/src/rvt-viewer-hl
State: committed on branch hl (not merged; c3-viewer merges). Smoke: tools/style_test.py (round trip of 5 styles, no JS errors) and node tools/hl_worker_test.js pass. Full demo smoke on this worktree not run (no .venv; use wrapper, see memory hl-worktree-testing.md).
Done: web/hl.js (styles Hidden Line default / Shaded / Consistent / Realistic / Wireframe, edge worker, silhouette in vertex shader, translucent twin pass, dashed levels/grids), app.js shader patches, rvtviewer/vg3d.py + vg3d_worker.py (resolved view graphics endpoint, cache VER 2, explain=True), tools: shot3d.py (--style --vg), style_test.py, hl_score.py, hl_table.py, review_shots.py (HL3D=1).
Measured: Snowdon Structural view 600158 line F1 0.885 (P 0.86 R 0.92) after registration. Earlier table before the hidden-element fix was poor on other 3D views (mean 0.34, hidden categories were not applied); a rerun (HL3D=1 review_shots then tools/hl_table.py 43_Snowdon_Towers_Sample_Structural) was in flight and its result not read.
Open: re-score other 3D views and check camera orientation of view 783735; surface patterns; yellow framing fills depend on sheets filter evaluation (note in ~/src/rvt-sheets/NEEDS-FROM-SHEETS.md); annotations in 3D; edge cache; huge-model test (23_rme_advanced via h1run).
DEMO NOTE: hidden line is now the default, so demo step 1 (textures house) needs Style: Realistic (select in header, or ?style=realistic); decide before merging to master. Rule to keep: node --check hl.js before saving.

## Update 2026-10-18
* Measured (tools/hl_table.py, Snowdon 43 Structural, 13 3D views): HLR views (7) mean line F1 0.88 (600158 .90, 783735 .80, 783844 .78, 783871 .87, 783882 .99, 783925 .96, 923315 .89). The 6 FlatColors views score 0.2-0.7: Revit draws them as Consistent Colors (flat grey/brown with cut faces), not hidden line. The earlier mean 0.34 was a script bug (review_shots read the wrong column for perspective, fixed).
* Shaded and Consistent Colors now also draw edges (as Revit's Show Edges). Hidden line adds grey cut caps for 3D views with a section box.
* Needed from reader: per-view display style (NEEDS-FROM-READER.md, ~/rvt-research) to open each view in its own style.
* Known gap: floors with deck profile show their deck grooves as edges (Revit shows a flat slab).
