#!/bin/bash
# host1 job (via h1run, env occ): (1) convert the reference models with the final code and write fidelity coverage to ~/.cache/rvt-viewer/h1-coverage.json, (2) the per-class acceptance sweep (tools/accept_h1.sh)
D="$(dirname "$(readlink -f "$0")")/.."; [ -n "$RVT_NOFAST" ] && export RVT_NOFAST
python - "$D" <<'PY'
import sys, os, json, time
D = sys.argv[1]; sys.path.insert(0, D)
from rvtviewer import build
C = os.path.expanduser('~/rvt-research/corpus'); res = {}
for name, f in [('residential-2020', '2020/20_Residential_Sample_Project'), ('facades-2026', '2026/58_Snowdon_Towers_Sample_Facades'), ('hvac-2024', '2024/42_Snowdon_Towers_Sample_HVAC'), ('structural-2024', '2024/43_Snowdon_Towers_Sample_Structural')]:
    out = os.path.expanduser('~/.cache/rvt-viewer/h1-' + name); t = time.time()
    try: m = build.convert('%s/%s.rvt' % (C, f), out, log=lambda *a: None)
    except BaseException as ex: res[name] = {'error': repr(ex)}; print(name, 'FAILED', ex, flush=True); continue
    hid = set(m.get('defaultHidden') or []); tot = {}
    for c, v in m['coverage'].items():
        if c in hid: continue
        for k, n in v.items(): tot[k] = tot.get(k, 0) + n
    res[name] = {'coverage': tot, 'secs': round(time.time() - t, 1), 'timings': m['timings']}; print(name, res[name], flush=True)
json.dump(res, open(os.path.expanduser('~/.cache/rvt-viewer/h1-coverage.json'), 'w'), indent=1)
PY
bash "$D/tools/accept_h1.sh"
