# HANDOFF c2-vctl (2026-10-15, stopped by orchestrator: user needs claude2)
Branch vctl, worktree ~/src/rvt-viewer-vctl, head = see `git log`. All work committed and tested (tools/vctltest.py ALL OK on Residential plan 180203 and section 29201; demo smoke OK before the last small commits).
## State
* View control v1 done: web/viewctl.js (overlay in model space, panel, picking, presets, depth-rank painter order, part/layer/category/type/element visibility, colour/weight/pattern overrides, text/symbol size, annotation scale / detail / template / filters / cut plane / phase re-render), rvtviewer/viewctl.py (API, proxies the sheets server's /sheets/api/{mid}/view/{id}.json when it exists, else rvtviewer/vscene_worker.py), vcache.py (content-keyed cache, stale fallback), tools/vctltest.py, tools/vc_warm.sh, docs/CONTROL-API.md (+ANSWERS).
* master merged an earlier vctl head; later vctl commits are NOT yet in master (tell c5-viewer; run smoke first). Master .venv was rebuilt after my symlink incident (see memory worktree-venv-symlink-incident); never `git add -A` a .venv symlink.
## Next
1. DONE 2026-10-15: release 3 mounted, scene served by the sheets server (X-Vc-Source: sheets) incl. uncached variants.
2. DONE: Structural scenes warmed (41, key b73c3265d16b52b5, 12 carry element props); re-warm only if the sheets drawing code changes.
3. Wire c2-annot's element properties (picking panel) when ViewDrawer.element_props lands; use `anchor` for true model-space placement; tags/grids `part` values when added.
4. Possible: 3D-view annotations, per-type (family type) grouping once typeName exists, better mask handling check on detail views, Revit-export comparison via c5-qa.
## Rules reminder
remote-host light only (MemoryMax 1.5G, stop servers/workers when done); no pkill -f patterns in own command line.

## Update 2026-10-16
* Text size/position accuracy vs Revit is covered by c5-qa (vector text diff vs Revit DXF: 1220 of 1295 texts matched, 94%, 43 views; see ~/src/rvt-qa/README.md). Viewer text uses the same size rule (em = size/0.72), so no viewer-side work left there.
* Done since: family-type visibility, picked properties, Also show (stacked views), hide far-out heads, warm of Structural/Residential/Commercial scenes. All merged in master.

## Final stop 2026-10-16
* Last commit adds a part/hang visibility check to tools/vctltest.py (ALL OK on Residential plan 180203). All earlier work is merged in master; this test commit is on vctl only.
* Idle items: tagged-element anchor from c2-annot; 3D/drafting/legend support (not started, would be a branch off vctl).
