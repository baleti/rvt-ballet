"""ESCAPE hunt (delete): a VALID output with wall 301553 really deleted, handed to the gate with a manifest that names another element as deleted, declares the wall only as 'modified', or declares nothing, must be refused (nothing written, source intact). The honest manifest passes."""
import os, sys, tempfile, hashlib, shutil
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save, edit
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
src = os.path.join(_T, 'src.rte'); shutil.copy(RTE, src); h0 = sha(src); W = 301553
ss = save.SaveSessions(); d = ss.doc('m', src)
nb, deleted = edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': W})]); assert nb != d.buf and deleted, deleted
op = edit.validate_op({'op': 'delete', 'eid': W}); m = save.Edits() if hasattr(save, 'Edits') else __import__('rvtballet.edit', fromlist=['Edits']).Edits(); m.ops = [op]
mf = m.manifest(deleted); ech = save.derived_echoes(d.buf, nb, edit.compose([op])); H = {'modified': sorted(set(mf['modified']) | {'el:%d' % i for i in ech}), 'deleted': list(mf['deleted'])}; print('honest manifest', H)
# KNOWN GATE GAP: 'extra_deleted_unrelated' (a still-present element declared deleted) is ACCEPTED by the savegate verify; reported in NEEDS-FROM-SAVEGATE.md. The product path is covered by save._readback at the end of this test.
res = {}
for name, man, ok in (('honest', H, True), ('wrong_deleted', dict(H, deleted=['el:%d' % (W + 1)]), False),
                      ('as_modified', {'modified': H['modified'] + ['el:%d' % W], 'deleted': []}, False), ('empty', {'modified': []}, False), ('extra_deleted_unrelated', dict(H, deleted=H['deleted'] + ['el:301595']), True)):
    dest = os.path.join(_T, 'o_%s.rte' % name)
    try: save.save_as(ss, 'm', src, dest, new_bytes=nb, manifest=man); acc = True; res[name] = 'ACCEPTED'
    except Exception as e: acc = False; res[name] = type(e).__name__
    assert acc == ok, (name, res)
    if not acc: assert not os.path.exists(dest), name
    assert sha(src) == h0
print(res); print('save escape delete OK')

# product-path layer: save._readback refuses an output where a declared delete did NOT happen (the gate alone accepts it, see above); an honest delete passes
dop = edit.validate_op({'op': 'delete', 'eid': 301595})
try: save._readback(d.buf, d.buf, [dop]); print('FAIL undone delete accepted by _readback'); sys.exit(1)
except save._import().VerifyFailed as x: print('refused undone delete:', str(x)[:100])
save._readback(d.buf, nb, [op])
print('save readback delete OK')
