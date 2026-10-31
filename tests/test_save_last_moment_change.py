"""The file is changed by another program AFTER the final pre-rename check but before the rename (simulated by wrapping atomic.commit_temp): the save completes, the result warns, and the other program's version is kept as a backup that RESTORE can bring back (nothing silently lost)."""
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sg = save._import(); from savegate import atomic
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
p = T + '/m.rte'; shutil.copy(S, p)
ss = save.SaveSessions(); d = ss.doc('m', p)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
real = atomic.commit_temp; other = {}
def racing(tmp, dst, *a, **k):
    b = bytearray(open(dst, 'rb').read()); b[-1] ^= 0xFF; open(dst, 'wb').write(bytes(b)); other['sha'] = sha(dst)      # the other program writes right before our rename
    return real(tmp, dst, *a, **k)
atomic.commit_temp = racing
try: r = save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']})
finally: atomic.commit_temp = real
assert sha(p) == hashlib.sha256(nb).hexdigest(), 'file is not our output'
W = r.get('warnings', []) + (r.get('verify') or {}).get('warnings', [])
assert any('another program changed' in w for w in W), r
assert r.get('warnings'), 'the warning is only buried in verify, not surfaced at top level'
assert any(sha(b['path']) == other['sha'] for b in save.backups(p)), 'the other program\'s version was not kept as a backup'
print('last-moment external change: warned, other version kept as backup (restorable)')
