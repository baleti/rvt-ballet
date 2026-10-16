# HANDOFF c5-vctl (2026-10-17, claude5 -> claude3)
Worktree ~/src/rvt-viewer-vctl, branch vctl. Everything committed; all code commits are merged in master (last: host-tag test 5ae62b1). Only PROGRESS notes are vctl-only. No h1run jobs running, no servers running.
## State
* View control v1 complete (see PROGRESS.md, docs/VIEW-CONTROL.md, docs/CONTROL-API.md). This session: tag symbols scale about their own first point when the prim has `host` (anchor = tagged element centre); drafting and legend views selectable (white sheet, framed top-down via frameFlat); vctltest has a synthetic host-tag check; `vctl.rebuild()` exposed.
* Scene caches re-warmed with sheets release 13 code on remote-host and pulled: Structural (41), Residential (17), Commercial (20). vctltest ALL OK on Residential 180203, Structural 124186 (VC_RERENDER=0), Commercial 193216.
* Merge protocol: tell c5-viewer the vctl commit in VCTL-HOOKS.md plus tmux nudge; they smoke then merge. Merge master into vctl regularly.
## Next steps
1. Re-warm again only if c5-sheets changes drawing code (tools/vc_warm.sh FILE NAME; h1run refuses below 11 GB MemAvailable; retry loop pattern: until vc_warm.sh ... | grep -q '^started'). Log in ~/demo-state/H1-QUEUE.md.
2. 3D views: scenes are served (camera 3D view returns ~3.7k prims) but annotation placement semantics are undecided; not started.
3. Drafting/legend: only checked on Residential 'gable end' drafting; no legend view tested.
4. Revit-export visual diff of the overlay via c5-qa.
## Gotchas
* Never `pkill -f` with a pattern that matches your own command line (kills your shell, exit 144).
* Test: start `bin/rvt-view FILE --no-browser --port N` under systemd-run MemoryMax=3G, then `python3 tools/vctltest.py URL VIEWID`; kill the server by pid.
