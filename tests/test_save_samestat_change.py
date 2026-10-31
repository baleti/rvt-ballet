"""The file is modified behind the viewer's back with the SAME size and the SAME mtime (content changed only): in-place SAVE! must still notice (Conflict) and leave that other program's version untouched."""
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
p = T + '/m.rte'; shutil.copy(S, p)
ss = save.SaveSessions(); d = ss.doc('m', p)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
st = os.stat(p); b = bytearray(open(p, 'rb').read()); b[-1] ^= 0xFF; open(p, 'wb').write(bytes(b)); os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))
assert os.stat(p).st_size == st.st_size and os.stat(p).st_mtime_ns == st.st_mtime_ns; h1 = sha(p)
try: save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']}); raise SystemExit('FAIL: save overwrote a file changed behind its back (same size and mtime)')
except SystemExit: raise
except Exception as e: err = type(e).__name__
assert sha(p) == h1, 'the other program\'s version was modified'
print('same-size same-mtime external change detected: %s, file untouched' % err)
