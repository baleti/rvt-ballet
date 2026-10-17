# HANDOFF c3-vctl (2026-10-17)
Worktree ~/src/rvt-viewer-vctl, branch vctl. View control v1 complete (docs/VIEW-CONTROL.md, docs/CONTROL-API.md). Nothing running; no servers, no h1run jobs.
## Done this session
* Legend/drafting paper look fixed (caps + level planes hidden; app.js exports window.__caps) - merged in master (deef646).
* Annotations header button moved next to #navSel (was off-screen at 1280 px) 24bedb5; visibility tabs wrap 26b0d44. NOT yet merged in master unless VCTL-HOOKS.md says so; demo_smoke OK on Residential, Structural 2024, Facades 2026.
* Tests: tools/vctltest.py (API), vcalign.py (placement vs reader grids, plans+sections, 0.00 mm), vcsweep.py (every view), vcui.py (real mouse). All OK on Residential, Commercial, Structural 2024, Facades 2026; sweep OK on Structural 2026 (55).
* Scenes re-warmed with rvt-sheets cb53624 for Residential, Commercial, Structural 2024, Facades 2026, Structural 2026 (55).
* 3D views: not overlaid by design (scene = projected model linework only).
## Next
1. Re-warm (tools/vc_warm.sh FILE NAME, retry until output has a line starting 'started'; pull the cache dir printed in the log) whenever rvt-sheets drawing code changes; log in ~/demo-state/H1-QUEUE.md. In zsh pass args explicitly (no `set -- $var`).
2. Keep merging master into vctl; tell c5-viewer the commit in VCTL-HOOKS.md plus tmux nudge.
3. Open: numeric visual diff vs Revit exports is covered by c3-qa on the same primitives; viewer-only rendering was checked by eye (Residential 180203).
## Gotchas
* Never `pkill -f` a pattern that appears in your own command line (kills your shell, exit 144); kill test servers by pid from `ss -ltnp`.
