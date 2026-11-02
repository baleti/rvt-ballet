"""Disk-full stand-in (RLIMIT_FSIZE, no root needed): an in-place SAVE! with a real edit where every write beyond N bytes fails (EFBIG, like ENOSPC mid-write).
Invariant over limits from 1 MB up to just below the file size: the save is refused (never 'SAVED' with a short file), the original is byte-identical, no stray temp/part file is left.
Child process per limit; Autodesk-derived 2024 template."""
import os, sys, shutil, tempfile, subprocess, hashlib
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
CH = r'''
import sys, os, signal, resource, json
here, p, lim = sys.argv[1], sys.argv[2], int(sys.argv[3]); sys.path.insert(0, here)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import save
ss = save.SaveSessions(); ss.doc("m1", p)
save.add_edit(ss, "m1", p, {"op": "set_string", "eid": 281147, "param": "Comments", "value": "FsizeTest"})
signal.signal(signal.SIGXFSZ, signal.SIG_IGN); resource.setrlimit(resource.RLIMIT_FSIZE, (lim, lim))
try: save.save_overwrite(ss, "m1", p); print("SAVED", flush=True)
except BaseException as e: print("REFUSED", type(e).__name__, flush=True)
'''
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
if not os.path.exists(SRC): print('skip'); sys.exit(0)
side = tempfile.mkdtemp(); open(side + '/g.json', 'w').write('{"rvt": {"*": "open"}}'); open(side + '/c.json', 'w').write('{"allow_overwrite": true}')
env = dict(os.environ, SAVEGATE_JOURNAL=side + '/j', SAVEGATE_CACHE=side + '/c', SAVEGATE_GATE=side + '/g.json', RVTBALLET_ALLOW_OVERWRITE='1', RVTPLAT_MEM_GB=os.environ.get('RVTPLAT_MEM_GB', '5'))
size = os.path.getsize(SRC); res = {}
for lim in (1 << 20, size // 2, size - 4096, size + 2048):      # last: limit just above size, an honest edit grows the file by little, may or may not fit
    w = tempfile.mkdtemp(); p = w + '/a.rvt'; shutil.copy(SRC, p); h0 = sha(p)
    r = subprocess.run([sys.executable, '-c', CH, HERE, p, str(lim)], env=env, capture_output=True, text=True, timeout=1800)
    out = (r.stdout.strip().splitlines() or ['CRASH ' + r.stderr[-200:]])[-1]
    left = sorted(f for f in os.listdir(w) if f != 'a.rvt')
    if out.startswith('SAVED'):
        assert os.path.getsize(p) <= lim, ('saved file larger than the limit', lim)
    else:
        assert out.startswith('REFUSED'), (lim, out)
        assert sha(p) == h0, ('original changed after refused save', lim)
    assert not [f for f in left if f.endswith(('.tmp', '.part')) or 'sgtmp' in f], ('stray temp', lim, left)
    res[lim] = out.split()[0] + ('/orig' if sha(p) == h0 else '/new'); shutil.rmtree(w, True)
print('fsize limit OK', res)
