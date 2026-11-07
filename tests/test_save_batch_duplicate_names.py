"""c5x-rvtread: two Level renames onto one name in a single in-place save: refused, original byte-identical (Autodesk 2024 template; skips when absent)."""
import os, sys, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); sys.path.insert(0, os.path.expanduser('~/src/rvt-viewer'))
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
for p in ('~/rvt-research','~/rvt-research/write-lab','~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w'))
os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
from rvtballet import save
save._import(); import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
if not os.path.exists(SRC): print("skip"); sys.exit(0)
p = _T + '/s.rvt'; shutil.copy(SRC, p); h0 = sha(p)
mk = lambda e, v, m: {'op': 'set_string', 'eid': e, 'field': 'DatumPlane.m_text', 'value': v, 'match': m}
try:
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', p)
    save.add_edit(ss, 'm', p, mk(5877, 'Same X', 'T.O. Slab')); save.add_edit(ss, 'm', p, mk(5855, 'same x', 'T.O. Fnd. Wall'))
    save.save_overwrite(ss, 'm', p); raise SystemExit('FAIL: duplicate batch saved')
except BaseException as e: print('refused', type(e).__name__, str(e)[:120])
assert sha(p) == h0; print('ok batch duplicate refused, original untouched')
