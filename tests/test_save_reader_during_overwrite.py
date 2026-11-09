"""in-place SAVE! (save_overwrite, gate forced open on a private copy) of move +2 ft AND rotate 30 of ONE instance (301595, cols2 scene): accepted, the file changes, then restore_backup returns the original byte-exact."""
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
import subprocess, time
f = _T + '/w.rte'; shutil.copy(S, f); h0 = sha(f); ss = save.SaveSessions(); d = ss.doc('m', f)
ops = [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 2.0, 'dy': 0.0, 'dz': 0.0})]
nb, _ = edit.apply_full(d.buf, ops); h1 = hashlib.sha256(nb).hexdigest()
W = 'import sys,os,hashlib,time\nf=sys.argv[1];seen={};t=time.time()\nopen(sys.argv[2],"w").write("1")\nwhile not os.path.exists(sys.argv[3]):\n    try: b=open(f,"rb").read()\n    except FileNotFoundError: b=b"MISSING"\n    h=hashlib.sha256(b).hexdigest() if b!=b"MISSING" else "MISSING"; seen[h]=seen.get(h,0)+1\nprint(repr(seen))\n'
w = subprocess.Popen([sys.executable, '-c', W, f, _T + '/ready', _T + '/stop'], stdout=subprocess.PIPE, text=True)
while not os.path.exists(_T + '/ready'): time.sleep(0.05)
save.save_overwrite(ss, 'm', f, new_bytes=nb, manifest={'modified': ['el:301595']})
save.restore_backup(ss, 'm', f)
time.sleep(0.3); open(_T + '/stop', 'w').write('1'); out = w.communicate(timeout=60)[0]; seen = eval(out)
print('observed states:', {k[:8]: v for k, v in seen.items()}, 'orig', h0[:8], 'new', h1[:8])
bad = [k for k in seen if k not in (h0, h1)]
assert not bad, 'reader saw a state that is neither the original nor the verified output: %s' % bad
assert sha(f) == h0
print('reader never saw a partial or missing file during SAVE! and RESTORE OK')
