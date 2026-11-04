"""(extreme moves) in-place SAVE! of a column moved 49999 ft and 1e-9 ft: gate must either accept with the file equal to the edited bytes, or refuse with the original untouched; never anything else. Prints which."""
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
ss = save.SaveSessions()
p = T + '/m.rte'; shutil.copy(S, p); h0 = sha(p); d = ss.doc('m', p)
for dx in (49999.0, 1e-9, -49999.0):
    shutil.copy(S, p); h0 = sha(p); d = ss.doc('m%s' % dx, p)
    nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': dx, 'dy': -dx, 'dz': dx / 2})])
    try:
        save.save_overwrite(ss, 'm%s' % dx, p, new_bytes=nb, manifest={'modified': ['el:301595']})
        assert sha(p) == hashlib.sha256(nb).hexdigest(); print(dx, 'ACCEPTED, file == edited bytes')
    except Exception as e:
        assert sha(p) == h0, 'refused but file changed'; print(dx, 'REFUSED', type(e).__name__, str(e)[:120], '- original intact')
