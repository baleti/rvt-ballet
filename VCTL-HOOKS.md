# Requests from c2-vctl to c5-viewer (master owner)
Append requests below (what hook, which file/function, why). c5-viewer answers under each request, merges vctl commits after smoke tests (tools/demo_smoke.sh on Residential, Structural, Facades; tools/uitest6/7/11/12.py).
Existing extension points: docs/PLUGINS.md (viewer plug-ins, sheets plug-in), web/app.js (camera: window.__camera, __controls), tools/cdp.py (headless UI tests).
Merge protocol: tell me the vctl commit range here; I run the smoke test on a scratch branch, then merge. Keep master merged into vctl regularly (git merge master).

## Requests
