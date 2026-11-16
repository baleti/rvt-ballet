"""c1x-rvtlink item 102/105: after link type A is set to an NFC path, setting link type B (another link type of the HVAC seed) to the NFD or case variant of it is refused by the duplicate guard. Seed ~/c5x-link/al/seed.rvt (two link types; skipped if absent)."""
import os, sys, struct
SEED = os.path.expanduser('~/c5x-link/al/seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LINKPATH'] = '1'
from rvtballet import edit, save
buf = open(SEED, 'rb').read()
P = save._read_params(buf)
types = sorted(e for e, d in P.items() if isinstance(d, dict) and d.get('class') == 'RvtLinkSymbol')
print('link types', types); assert len(types) >= 2 and 1363937 in types
A = 1363937; B = [t for t in types if t != A][0]
out = edit.apply(buf, [{'op': 'set_link_path', 'eid': A, 'value': 'Café.rvt'}]); out = out[0] if isinstance(out, tuple) else out
for v in ('Café.rvt', 'CAFÉ.RVT', 'Café.rvt'):
    try: edit.apply(out, [{'op': 'set_link_path', 'eid': B, 'value': v}])
    except edit.EditError as e: assert 'one link type per file' in str(e), (v, str(e)); continue
    raise SystemExit('duplicate accepted %r' % v)
print('OK NFD/case duplicate refused across two link types')
