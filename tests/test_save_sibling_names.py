"""(sibling names) Files named like a backup/temp of the source (m.rte.bak, m.rte~, m.bak, m.rte.orig, m.rte.tmp, m.rte.new, ~m.rte) already beside the source must survive in-place SAVE! and RESTORE byte-identical."""
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
sib = ['m.rte.bak','m.rte~','m.bak','m.rte.orig','m.rte.tmp','m.rte.new','~m.rte','m.rte.sgtmp','m (1).rte','m.rte.1','m.0001.rte','m.0002.rte','m.rte.lock','m.rte.lck','m.slog','m.rte.sgtmp.0']
for i, n in enumerate(sib): open(T + '/' + n, 'wb').write(('sentinel%d' % i).encode() * 5000)
snap = {n: sha(T + '/' + n) for n in sib}
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']})
assert sha(p) == hashlib.sha256(nb).hexdigest()
assert {n: sha(T + '/' + n) for n in sib} == snap, 'a sibling file was touched by SAVE!'
save.restore_backup(ss, 'm', p, 0)
assert sha(p) == h0 and {n: sha(T + '/' + n) for n in sib} == snap
print('sibling backup-like names untouched: save + restore OK')
