"""c3x-rvtmatrix: in-place SAVE! and RESTORE keep a POSIX ACL (system.posix_acl_access, extra named-user entry) on the source: a rename-over write that drops it silently widens or narrows access."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(_T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)

sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
f = _T + '/x.rte'; shutil.copy(S, f)
import struct
ACL = struct.pack('<I', 2) + b''.join(struct.pack('<HHI', t, p, i) for t, p, i in ((1, 6, 0xFFFFFFFF), (2, 4, 1234), (4, 4, 0xFFFFFFFF), (0x10, 6, 0xFFFFFFFF), (0x20, 0, 0xFFFFFFFF)))
try: os.setxattr(f, 'system.posix_acl_access', ACL)
except OSError as e: print('skip: ACLs unsupported', e); sys.exit(0)
m0 = os.stat(f).st_mode & 0o777; h0 = sha(f); ss = save.SaveSessions(); d = ss.doc('m', f)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0})])
save.save_overwrite(ss, 'm', f, new_bytes=nb, manifest={'modified': ['el:301595']})
assert open(f, 'rb').read() == nb
acl = os.getxattr(f, 'system.posix_acl_access'); print('ACL bytes after save:', len(acl))
assert acl == ACL, 'SAVE! dropped or changed the POSIX ACL'
save.restore_backup(ss, 'm', f); assert sha(f) == h0
assert os.getxattr(f, 'system.posix_acl_access') == ACL, 'restore dropped the ACL'
print('ACL survives save and restore OK')
