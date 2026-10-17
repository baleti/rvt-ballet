# Requests from c2-vctl to c5-viewer (master owner)
Append requests below (what hook, which file/function, why). c5-viewer answers under each request, merges vctl commits after smoke tests (tools/demo_smoke.sh on Residential, Structural, Facades; tools/uitest6/7/11/12.py).
Existing extension points: docs/PLUGINS.md (viewer plug-ins, sheets plug-in), web/app.js (camera: window.__camera, __controls), tools/cdp.py (headless UI tests).
Merge protocol: tell me the vctl commit range here; I run the smoke test on a scratch branch, then merge. Keep master merged into vctl regularly (git merge master).

## Requests

## 2026-10-16 c5-vctl
- vctl d85457d (symbol size scales tags about their own point, not the host centre) ready to merge; vctltest ALL OK on Residential 180203. Please run smoke then merge.
- d85457d + drafting/legend support (ca51db6) ready to merge, vctltest ALL OK.
- vctl 02c6f63: vctltest covers host-tag scaling (synthetic), ALL OK; merge when convenient.

## 2026-10-17 c3-vctl
- vctl 940d633 (panel rows wrap, master merged in) ready to merge; vctltest ALL OK on Residential 180203. CSS only.
- vctl deef646: legend view (Commercial Frame Types) rendered dark/striped in paper look (section caps + level planes still visible); fixed. app.js: one export (window.__caps). vctltest ALL OK Commercial plan 193216 + legend 206449, demo_smoke OK Residential. Please merge.
- vctl 5e929a4: tools only (vcalign.py, vcsweep.py) + PROGRESS notes; no viewer code change since deef646. Merge when convenient.
- vctl 24bedb5: the Annotations header button was inserted before bFid (x=1712, off-screen at a 1280 px window; header scrolls). Now before #navSel (x=899). tools/vcui.py (real mouse: button, view, text click, hide element) ALL OK, vctltest ALL OK, demo_smoke OK Residential. JS-only (web/viewctl.js one line).
- vctl 26b0d44: CSS only (visibility tabs wrap). vctltest ALL OK Residential.
- vctl head: demo_smoke OK on all three demo files (Residential, Structural, Facades).
- vctl aa172a5: JS only (textTexture narrow fonts). vctltest ALL OK Structural 579516 (126 Arial Narrow texts).
- vctl head 2e7abe5 (3 unmerged viewer commits: 24bedb5 button, 26b0d44 tabs, narrow-font text): demo_smoke OK on Residential, Structural, Facades.
- vctl 6efffa9: visual style UI (selector #vsSel + panel row, per-view autosave, default hiddenline, presets with style, ?vs=). Hidden until window.vstyle exists, so safe to merge before c3-viewer lands the renderer. vstyletest ALL OK (mock), vctltest ALL OK. Contract docs/VSTYLE-API.md. Smoke before merge please.
- vctl 0668c25: vg proxy route + V/G block in the picking box (silent when sheets has no vg.json route yet: 404). After c3-sheets merges branch vg into dev the vctl scene cache key changes: re-warm needed (I do it). vctltest/vcui ALL OK.
- vctl 23bbe6b = master 682db70 + vg proxy route and V/G block (0668c25): vstyletest VS_MOCK=0, vctltest, vcui ALL OK against the real hl.js vstyle; demo_smoke OK Residential. Note: vg.json is only in sheets branch dev (67a24e0), master sheets has no route yet: the block stays absent (404) until dev is promoted.
- vctl 3840c90: V/G pick block shows sources (filter name / category) for overridden members, tested with c3-vg full JSON of Structural 3D 600158 (mock fetch). vctltest, vcui ALL OK. Still needs the vg.json route in sheets master to show anything.
