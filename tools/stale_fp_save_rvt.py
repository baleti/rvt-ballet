"""stale_fp_save_rvt.py FILE.rfa|rvt... : the model is loaded (ss.doc), THEN the file on disk changes (1 flipped byte, only mtime touched, other bytes appended, replaced by different content, deleted), THEN save_overwrite (gate open, throwaway config). Must be REFUSED with the on-disk bytes exactly as the other program left them (mtime-only may be refused or saved). Exit 1 on any overwrite of foreign content."""
import os, sys, shutil, tempfile, hashlib, subprocess
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = r'''
import sys, os
here, p, mode, other = sys.argv[1:5]; sys.path.insert(0, here)
from rvtballet import save
ss = save.SaveSessions(); ss.doc("m1", p)
b = open(p, "rb").read()
if mode == "flip1": d = bytearray(b); d[len(d)//2] ^= 1; open(p, "wb").write(d)
elif mode == "touch": os.utime(p, (1, 1))
elif mode == "append": open(p, "ab").write(b"x")
elif mode == "other": open(p, "wb").write(open(other, "rb").read())
elif mode == "deleted": os.remove(p)
try: save.save_overwrite(ss, "m1", p); print("SAVED")
except BaseException as e: print("REFUSED", type(e).__name__)
'''
bad = 0; other = sorted(sys.argv[1:])[0]
for f in sys.argv[1:]:
    for mode in ('flip1', 'touch', 'append', 'other', 'deleted'):
        w = tempfile.mkdtemp(); side = tempfile.mkdtemp(); p = os.path.join(w, 'a' + os.path.splitext(f)[1]); shutil.copy(f, p)
        oth = os.path.join(side, 'o.bin'); open(oth, 'wb').write(open(f, 'rb').read()[:-1] + b'Z')      # same size, different content
        open(side + '/c.json', 'w').write('{"allow_overwrite": true}'); open(side + '/g.json', 'w').write('{"rvt": {"*": "open"}}')
        env = dict(os.environ, PYTHONPATH=os.path.expanduser('~/src/savegate'), SAVEGATE_JOURNAL=side + '/j', SAVEGATE_CACHE=side + '/c', DWG_BALLET_CONFIG=side + '/c.json', SAVEGATE_GATE=side + '/g.json', RVTBALLET_ALLOW_OVERWRITE='1')
        r = subprocess.run([sys.executable, '-c', CH, HERE, p, mode, oth], env=env, capture_output=True, text=True, timeout=1800)
        res = (r.stdout.strip().splitlines() or ['NOOUT ' + r.stderr[-80:]])[-1]
        # state the child left right before save_overwrite is not observable; recompute expected foreign bytes
        src = open(f, 'rb').read(); exp = {'flip1': None, 'touch': src, 'append': src + b'x', 'other': open(oth, 'rb').read(), 'deleted': None}[mode]
        if mode == 'flip1': d = bytearray(src); d[len(d)//2] ^= 1; exp = bytes(d)
        now = open(p, 'rb').read() if os.path.exists(p) else None
        if mode == 'touch': ok = res.startswith('SAVED') or now == src
        else: ok = res.startswith('REFUSED') and now == exp
        print(os.path.basename(f)[-14:], mode, res, 'OK' if ok else 'BAD', flush=True); bad += not ok; shutil.rmtree(w, True); shutil.rmtree(side, True)
sys.exit(1 if bad else 0)
