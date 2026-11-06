"""MOVE-AMOUNT ESCAPE hunt: declared move dx=1 of e; bytes actually moved e by dx=7 (same element) -> raw gate vs product _readback; and moved e2 instead of e. Derived from: ESCAPE hunt on a REAL file: the gate is handed bytes where TWO elements' strings changed (Mark of e and Comments/Mark of e2) while the manifest declares only e. In-place save_overwrite must REFUSE and leave the file byte-identical. Also: declared e but bytes changed only e2 (wrong element). usage: rvtsave_escape_real.py SRC.rvt. Private copy; aggregate output."""
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
c = [e for e, v in sorted(pr.items()) if e >= 1000 and v.get('class') == 'FamilyInstance' and isinstance(v.get('params', {}).get('Mark'), str)][:2]
e1, e2 = c
mv = lambda eid, dx: edit.validate_op({'op': 'move', 'eid': eid, 'dx': dx})
res = {}
for name, nb_ops, decl in (('declared_dx1_actual_dx7', [mv(e1, 7.0)], [e1]), ('declared_e1_actually_moved_e2', [mv(e2, 1.0)], [e1])):
    nb, _ = edit.apply_full(d.buf, nb_ops); ss = save.SaveSessions(); ss.doc('m', p)
    try: save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:%d' % x for x in decl]}); res['raw_gate_' + name] = 'ACCEPTED file_changed=%s' % (sha(p) != h0); shutil.copy(sys.argv[1], p)
    except BaseException as x: res['raw_gate_' + name] = 'refused:' + type(x).__name__ + ':' + str(x)[:70].replace('\n', ' '); res['untouched_' + name] = sha(p) == h0
    try: save._readback(d.buf, nb, edit.compose([mv(e1, 1.0)])); res['product_readback_' + name] = 'NOT CAUGHT (ESCAPE)'
    except BaseException as x: res['product_readback_' + name] = 'caught:' + type(x).__name__ + ':' + str(x)[:90].replace('\n', ' ')
print(json.dumps(res, indent=1)); sys.exit(0 if not any('ESCAPE' in str(v) for v in res.values()) else 1)
