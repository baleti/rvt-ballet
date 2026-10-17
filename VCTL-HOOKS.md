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
