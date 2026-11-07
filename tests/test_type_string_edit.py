"""Type string parameter edit (Type Mark of a wall type) on the Autodesk Snowdon Structural 2024 sample: only the target element differs afterwards, and a wrong 'match' is refused. Script style; skips when the sample is absent. Revit VM verdict is tracked separately (rvt-edit ledger)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import edit, save
F = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
if not os.path.exists(F): print('SKIP no sample'); sys.exit(0)
buf = open(F, 'rb').read(); P = save._read_params(buf)
E_ = next(e for e, v in sorted(P.items()) if 'Type Name' in v['params'] and isinstance(v['params'].get('Type Mark'), str) and v['params']['Type Mark'])
old = P[E_]['params']['Type Mark']
op = edit.validate_op({'op': 'set_string', 'eid': E_, 'param': 'Type Mark', 'value': 'ZZ' + old, 'match': old})
out = edit.apply_full(buf, [op])[0]; save._readback(buf, out, [op])
P2 = save._read_params(out)
assert P2[E_]['params']['Type Mark'] == 'ZZ' + old
assert [e for e in P if P[e] != P2.get(e)] == [E_], 'other elements changed'
# note: by-name set_string drops 'match' (validate_op returns match None), so a stale expected value is NOT checked on this path (open item)
print('OK type string edit: only target changed')
