"""(restore chain) Three in-place SAVE!s in a row (each from a fresh load of the previous result); then RESTORE n=0..2 must each give exactly the bytes that existed before save (3-n)... i.e. every historic version is recoverable byte-exact, newest first."""
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
states = [h0]; cur = p
for k in range(3):
    dd = ss.doc('m%d' % k, p)
    nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0 + k})])
    save.save_overwrite(ss, 'm%d' % k, p, new_bytes=nb, manifest={'modified': ['el:301595']})
    assert sha(p) == hashlib.sha256(nb).hexdigest(); states.append(sha(p))
assert len(set(states)) == 4
bk = save.backups(p); by = {sha(b['path']): b['n'] for b in bk}
assert len(bk) >= 3, bk
for k in (0, 1, 2):     # every state before a save is held as a backup, found by content
    assert states[k] in by, 'state %d not among backups' % k
for k in (2, 1, 0):     # restore each by its index at that moment (indexes shift as restore backs up the current file)
    bk = save.backups(p); n = next(b['n'] for b in bk if sha(b['path']) == states[k])
    save.restore_backup(ss, 'mr', p, n)
    assert sha(p) == states[k], 'restore of state %d returned other bytes' % k
print('all 3 historic states restored byte-exact; backups now', len(save.backups(p)))
