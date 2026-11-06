"""SAME-ELEMENT ESCAPE hunt (MaterialElem has Mark+Comments+Description strings): declared edit = Mark of m; bytes ALSO change its Comments and Description. Must be refused or, if accepted, is a granularity ESCAPE. Derived from: ESCAPE hunt on a REAL file: the gate is handed bytes where TWO elements' strings changed (Mark of e and Comments/Mark of e2) while the manifest declares only e. In-place save_overwrite must REFUSE and leave the file byte-identical. Also: declared e but bytes changed only e2 (wrong element). usage: rvtsave_escape_real.py SRC.rvt. Private copy; aggregate output."""
import os, sys, tempfile, json, shutil, hashlib
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ.update(SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', RVTBALLET_SNAPSHOT_CACHE='0', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=T + '/gate.json')
json.dump({'rvt': {'2024': 'open', '2026': 'open'}}, open(T + '/gate.json', 'w'))
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]
from rvtballet import save, edit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
p = T + '/m.rvt'; shutil.copy(sys.argv[1], p); h0 = sha(p)
ss = save.SaveSessions(); d = ss.doc('m', p)
pr = save._read_params(d.buf)
c = [e for e, v in sorted(pr.items()) if e >= 1000 and v.get('class') == 'MaterialElem' and all(isinstance(v['params'].get(k), str) for k in ('Mark', 'Comments', 'Description'))]
m = c[0]
def ed(eid, par, val): return edit.validate_op({'op': 'set_string', 'eid': eid, 'param': par, 'value': val, 'match': pr[eid]['params'][par]})
cases = {'declared_Mark_also_Comments_changed': [ed(m, 'Mark', 'LieM'), ed(m, 'Comments', 'LieC')], 'declared_Mark_only_Comments_changed': [ed(m, 'Comments', 'LieC')]}
res = {}
for name, ops in cases.items():
    nb, _ = edit.apply_full(d.buf, ops); ss = save.SaveSessions(); ss.doc('m', p)
    try:
        save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:%d' % m]}); res[name] = 'ACCEPTED'
    except BaseException as x: res[name] = 'refused:' + type(x).__name__ + ':' + str(x)[:80].replace('\n', ' ')
    if res[name] == 'ACCEPTED': res[name] += ' file_changed=%s' % (sha(p) != h0); shutil.copy(sys.argv[1], p)
    else: res[name + '_file_untouched'] = sha(p) == h0
# the product path (_pending) runs _readback over the DECLARED ops: does it catch the extra Comments change?
nb, _ = edit.apply_full(d.buf, [ed(m, 'Mark', 'LieM'), ed(m, 'Comments', 'LieC')])
try: save._readback(d.buf, nb, edit.compose([ed(m, 'Mark', 'LieM')])); res['product_readback_declared_Mark_only'] = 'NOT CAUGHT (ESCAPE)'
except BaseException as x: res['product_readback_declared_Mark_only'] = 'caught:' + type(x).__name__ + ':' + str(x)[:90]
print(json.dumps(res, indent=1)); sys.exit(0 if not any('ESCAPE' in str(v) for v in res.values()) else 1)
