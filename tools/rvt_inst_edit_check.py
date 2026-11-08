#!/usr/bin/env python3
"""rvt_inst_edit_check.py FILE.rvt OUTDIR [N]: move +1 ft and delete up to N FamilyInstances (writer, rvtedit backend), save under OUTDIR
(a scratch dir, never the source), then run rvt_target_check on each. Aggregate lines only. Autodesk samples / synthetic only."""
import os, sys, subprocess
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(here, '..'))
from rvtballet import edit
import rvtballet.edit as E
sys.path.insert(0, E.WL); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
import rvt_geometry as G
F, OUT = sys.argv[1], sys.argv[2]; N = int(sys.argv[3]) if len(sys.argv) > 3 else 2
os.makedirs(OUT, exist_ok=True); buf = open(F, 'rb').read()
ids = [e for e, v in G.file_geometry_index(F).items() if str(v) == 'FamilyInstance'][:int(os.environ.get("POOL", N * 6))]
res = {'move': [0, 0, 0], 'delete': [0, 0, 0]}   # accepted, clean, stray
done = {'move': 0, 'delete': 0}
for e in ids:
    for kind in ('move', 'delete'):
        if done[kind] >= N: continue
        op = {'op': 'move', 'eid': e, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0} if kind == 'move' else {'op': 'delete', 'eid': e}
        try: _r = edit.apply_full(buf, [edit.validate_op(op)]); out = _r[0]; owned = [int(x) for x in (_r[1] if len(_r) > 1 else [])]
        except Exception as x: continue
        done[kind] += 1; res[kind][0] += 1
        p = os.path.join(OUT, '%s_%d.rvt' % (kind, e)); open(p, 'wb').write(out)
        r = subprocess.run([sys.executable, os.path.join(here, 'rvt_target_check.py'), F, p, '--target', str(e)] + (['--delete', '--allow', ','.join(map(str, owned))] if kind == 'delete' else []), capture_output=True, text=True)
        res[kind][1 if r.returncode == 0 else 2] += 1
        print(kind, e, r.stdout.strip()[:160], flush=True)
print('SUMMARY (accepted, clean, stray):', res)
