# HANDOFF c3-vctl (updated 2026-10-18)
Worktree ~/src/rvt-viewer-vctl, branch vctl. Nothing running (no servers, no h1run jobs). View control v1 complete (docs/VIEW-CONTROL.md, docs/CONTROL-API.md), plus the visual-style UI.
## Done
* Panel/overlay: legend/drafting paper look fix, button visible at 1280 px, wrapping rows/tabs, Arial Narrow width, picking box with Revit V/G block (proxy /api/m/{mid}/vc/vg/{vid} -> sheets vg.json; filter/category sources via ?full=1 elements_src).
* Visual style (contract docs/VSTYLE-API.md, c3-viewer implements window.vstyle in hl.js): header select #vsSel + panel row + 'Style options' row (edge angle, silhouettes, hidden lines, line weight, face colour), per-view autosave localStorage vstyle:{mid}:{view|model}, default 'hiddenline' (vstyle:default, ?vs=), presets carry style, view default from meta views[].display.vstyle (0/1 flags mapped; late display re-read once after 10 s).
* Tools: vctltest.py, vcalign.py (placement vs reader grids, plans+sections 0.00 mm), vcsweep.py (every view), vcui.py (real mouse), vstyletest.py (VS_MOCK=0 for the real vstyle). All need headless chromium: NOT available on remote-host; on remote-host only single-view Residential-size checks capped at 1.5 GB (user rule, memory guard kills big jobs).
## State at handoff
* Last vctl head merged into master unless VCTL-HOOKS.md lists newer commits (late display, 0/1 flags: ask c3-viewer to merge).
* Scene caches (tools/vc_warm.sh FILE NAME on remote-host, pull one dir per h1run call): Residential, Commercial, Structural 2024 current with sheets 0cb42bd; Facades 2026 QUEUED in ~/demo-state/H1-QUEUE.md (remote-host MemAvailable was < 11 GB each try; single attempt per keepalive, no loops).
## Next
1. Facades re-warm when remote-host has 11 GB; re-warm all four after any rvt-sheets drawing-code change (schedule-only commits do not stale scenes).
2. Merge master into vctl regularly (PROGRESS.md conflicts: keep both sides).
3. Open decision for the user: install chromium on remote-host so sweeps/UI tests can run there.
4. Optional: show 'colour from filter X' with real data once a view with filters is sampled in a browser test; extend style options as hl.js adds them.
## Gotchas
* Never `pkill -f` with a pattern in your own command line; kill test servers by pid from `ss -ltnp`. zsh does not word-split unquoted variables (use ${=var}). h1run pull with several dirs in one call breaks the pipe: one dir per call.
