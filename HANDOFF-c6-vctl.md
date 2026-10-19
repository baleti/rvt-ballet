# HANDOFF c6-vctl (2026-10-19)
Worktree ~/src/rvt-viewer-vctl, branch vctl. View control v1 + visual-style UI complete (docs/VIEW-CONTROL.md, CONTROL-API.md, VSTYLE-API.md). Viewer code on vctl is merged-ready; see VCTL-HOOKS.md for commits for c5-viewer to merge (smoke first).
## Verification routine (remote-host, single Residential file only)
ALLOW_remote-host=1 tools/demo_smoke.sh FILE PORT; start bin/rvt-view FILE --no-browser --port 8898, wait ~12 s, then tools/vctltest.py and tools/vcui.py URL 180203 (capped 1.5 GB). A first run right after a smoke run can time out once (cold start): rerun.
## Queue
* Commercial re-warm (tools/vc_warm.sh FILE NAME on remote-host) waits for the remote-host memory gate (known, do not report). Structural warmed (cache dir 7fa5aad359029116 pulled). Facades, Residential current as of sheets 0cb42bd; re-warm after any rvt-sheets drawing-code change.
* vc_warm_sheets.py now prints the dir of the newest scene file (the earlier printed dir did not exist on remote-host).
## Open
* Live browser check of 'colour from filter' on a filtered Snowdon Structural view (needs chromium on remote-host or a big remote-host run: parked).
* Annotation classes not yet drawn by sheets: angular/radial dimensions, revision clouds.
* 3D views carry no annotation overlay.
