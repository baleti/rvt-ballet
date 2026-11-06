"""ESCAPE hunt on a REAL file: the gate is handed bytes where TWO elements' strings changed (Mark of e and Comments/Mark of e2) while the manifest declares only e. In-place save_overwrite must REFUSE and leave the file byte-identical. Also: declared e but bytes changed only e2 (wrong element). usage: rvtsave_escape_real.py SRC.rvt. Private copy; aggregate output."""
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
c = [e for e, v in sorted(pr.items()) if e >= 1000 and isinstance(v.get('params', {}).get('Mark'), str)][:2]
e1, e2 = c
def ed(eid, val): return edit.validate_op({'op': 'set_string', 'eid': eid, 'param': 'Mark', 'value': val, 'match': pr[eid]['params']['Mark']})
both, _ = edit.apply_full(d.buf, [ed(e1, 'LieA'), ed(e2, 'LieB')])
only2, _ = edit.apply_full(d.buf, [ed(e2, 'LieB')])
res = {}
for name, nb, declared in (('extra_element_changed', both, [e1]), ('wrong_element_declared', only2, [e1])):
    try:
        save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:%d' % x for x in declared]}); res[name] = 'ACCEPTED'
    except BaseException as x: res[name] = 'refused:' + type(x).__name__ + ':' + str(x)[:80].replace('\n', ' ')
    res[name + '_file_untouched'] = sha(p) == h0
    if res[name] == 'ACCEPTED': shutil.copy(sys.argv[1], p)
print(json.dumps(res, indent=1)); sys.exit(0 if all(v is True or str(v).startswith('refused') for v in res.values()) else 1)
