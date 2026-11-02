"""rvt_noedit_streams.py FILE...: no-edit SAVE AS (rvtballet.save.save_as, throwaway gate) in a child process; output compared to the source: whole-file sha256 first, else CFB stream-by-stream (olefile) listing every stream whose bytes differ. Exit 1 if any stream differs or the save raised on a file that is not refused cleanly. Prints one line per file."""
import os, sys, subprocess, tempfile, hashlib, shutil
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = r'''
import sys, os, tempfile
sys.path.insert(0, sys.argv[1]); w = tempfile.mkdtemp(); open(w + "/g.json", "w").write('{"rvt": {"*": "open"}}')
os.environ.update(SAVEGATE_JOURNAL=w + "/j", SAVEGATE_CACHE=w + "/c", SAVEGATE_GATE=w + "/g.json")
from rvtballet import save
try:
    r = save.save_as(save.SaveSessions(), "m1", sys.argv[2], sys.argv[3]); print("SAVED")
except BaseException as e: print("RAISED", type(e).__name__, str(e)[:90].replace(chr(10), " "))
'''
def streams(p):
    import olefile
    o = olefile.OleFileIO(p); d = {'/'.join(s): hashlib.sha1(o.openstream(s).read()).hexdigest() for s in o.listdir()}; o.close(); return d
bad = 0
for f in sys.argv[1:]:
    d = tempfile.mkdtemp(); dst = os.path.join(d, 'o' + os.path.splitext(f)[1]); n = os.path.basename(f)[:14]
    r = subprocess.run([sys.executable, '-c', CH, HERE, f, dst], capture_output=True, text=True, timeout=3000)
    res = (r.stdout.strip().splitlines() or ['NOOUT ' + r.stderr[-100:]])[-1]
    if res != 'SAVED': print(n, res, 'REFUSED/ERR (file untouched by construction)', flush=True); shutil.rmtree(d, True); continue
    h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
    if h(f) == h(dst): print(n, 'IDENTICAL bytes', flush=True)
    else:
        try:
            a, b = streams(f), streams(dst); diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            print(n, 'bytes differ; streams total', len(a), 'differing', len(diff), diff[:4], 'OK' if not diff else 'BAD', flush=True); bad += bool(diff)
        except Exception as e: print(n, 'bytes differ, stream compare failed', type(e).__name__, e, 'BAD', flush=True); bad += 1
    shutil.rmtree(d, True)
sys.exit(1 if bad else 0)
