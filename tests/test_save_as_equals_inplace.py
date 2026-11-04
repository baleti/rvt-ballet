"""(determinism) The same edit saved with SAVE AS (new file) and with in-place SAVE! gives byte-identical files; repeating the edit twice gives the same bytes both times."""
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
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
nb2, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
assert nb == nb2, 'apply_full is not deterministic'
q = T + '/new.rte'
save.save_as(ss, 'm', p, q, new_bytes=nb, manifest={'modified': ['el:301595']})
save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']})
assert sha(q) == sha(p) == hashlib.sha256(nb).hexdigest(), 'SAVE AS and SAVE! differ'
print('deterministic; SAVE AS == SAVE! bytes', sha(p)[:12])
