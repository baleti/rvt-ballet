#!/usr/bin/env python3
"""rvt_type_edit_check.py FILE.rvt OUTDIR [N]: change_type (same-family swap) on up to N FamilyInstances, save under OUTDIR, run rvt_target_check. Autodesk samples only."""
import os, sys, subprocess
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_CHANGETYPE'] = '1'
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(here, '..'))
from rvtballet import edit
import rvtballet.edit as E
sys.path.insert(0, E.WL); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
import rvt_geometry as G
F, OUT = sys.argv[1], sys.argv[2]; N = int(sys.argv[3]) if len(sys.argv) > 3 else 2
os.makedirs(OUT, exist_ok=True); buf = open(F, 'rb').read(); ix = G.file_geometry_index(F)
inst = [e for e, v in ix.items() if str(v) == 'FamilyInstance'][:int(os.environ.get('POOL', 60))]
syms = [e for e, v in ix.items() if str(v) == 'FamilySymbol']
sys.path.insert(0, E.EL); os.environ.setdefault("RVT_GEOM", "1")
import rvtedit
ed = rvtedit.Edit(F); _fm = {}
def fam_of(sy):
    if sy not in _fm: _fm[sy] = E._field64(ed, sy, 'FamilySymbol.m_familyId')
    return _fm[sy]
print('instances', len(inst), 'symbols', len(syms)); done = 0; refused = {}
for e in inst:
    if done >= N: break
    cur = E._field64(ed, e, 'FamilyInstance.m_masterSymbolId')
    fc = fam_of(cur) if cur else None
    if fc is None: continue
    alt = next(([s] for s in syms if s != cur and fam_of(s) == fc), [])
    if not alt: refused['no sibling type'] = refused.get('no sibling type', 0) + 1; continue
    s = alt[0]
    try: out = edit.apply_full(buf, [edit.validate_op({'op': 'change_type', 'eid': e, 'type_eid': s})])[0]
    except Exception as x: k = str(x)[:60]; refused[k] = refused.get(k, 0) + 1; continue
    p = os.path.join(OUT, 'type_%d_%d.rvt' % (e, s)); open(p, 'wb').write(out); done += 1
    r = subprocess.run([sys.executable, os.path.join(here, 'rvt_target_check.py'), F, p, '--target', str(e)], capture_output=True, text=True)
    print('type', e, cur, '->', s, r.stdout.strip()[:150], flush=True)
print('accepted', done, 'refusal kinds', sorted(refused.items(), key=lambda x: -x[1])[:3])
