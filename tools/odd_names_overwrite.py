"""odd_names_overwrite.py FILE.rfa|rvt... : in-place SAVE! (rvtballet.save.save_overwrite, no edit) of a copy under hostile file names (spaces, quotes, unicode, emoji, leading dash, 200 chars, newline, tab, #%&;$, UPPER, leading dot, multi dot). Each must end SAVED (output identical to source or valid) or cleanly refused with the original byte-identical; no stray tmp/part/lock files beside the file (a .savegate backup folder is by design). One child process per name."""
import os, sys, shutil, tempfile, subprocess, hashlib
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = ['a b  c', "q'uote\"", 'münchen äö', '中文图', 'emoji\U0001F600', '-dash', 'x' * 200, 'new\nline', 'tab\tname', '#%25&;$', 'UPPER', '.hidden', 'a.b.c']
CHILD = r'''
import sys, os
sys.path.insert(0, sys.argv[1])
from rvtballet import save
ss = save.SaveSessions(); p = sys.argv[2]
try:
    r = save.save_overwrite(ss, "m1", p); print("SAVED", str(r.get("status", ""))[:20])
except BaseException as e: print("RAISED", type(e).__name__, str(e)[:70].replace(chr(10), " "))
'''
bad = 0
for f in sys.argv[1:]:
    ext = os.path.splitext(f)[1]
    for nm in NAMES:
        w = tempfile.mkdtemp(prefix='on-', dir=os.environ.get('TMPDIR')); p = os.path.join(w, nm + ext)
        try: shutil.copy(f, p)
        except OSError as e: print('skip', repr(nm[:12]), e); shutil.rmtree(w, True); continue
        side = tempfile.mkdtemp(prefix='side-')
        open(side + '/g.json', 'w').write('{"rvt": {"*": "open"}}')
        env = dict(os.environ, SAVEGATE_GATE=side + '/g.json', SAVEGATE_JOURNAL=side + '/j', SAVEGATE_CACHE=side + '/c', RVTBALLET_ALLOW_OVERWRITE='1')
        h0 = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        r = subprocess.run([sys.executable, '-c', CHILD, HERE, p], capture_output=True, text=True, env=env, timeout=900)
        res = (r.stdout.strip().splitlines() or ['NOOUT ' + r.stderr[-80:]])[-1]
        same = hashlib.sha256(open(p, 'rb').read()).hexdigest() == h0
        left = sorted(x for x in os.listdir(w) if x != '.savegate'); bk = os.listdir(w + '/.savegate') if os.path.isdir(w + '/.savegate') else []
        ok = (res.startswith('SAVED') or (res.startswith('RAISED') and same)) and left == [nm + ext] and all(b.startswith(nm) for b in bk)
        print(os.path.basename(f)[:10], repr(nm[:14]), res[:80], 'same' if same else 'changed', 'OK' if ok else 'BAD ' + repr(left[:3] + bk[:2]), flush=True); bad += not ok
        shutil.rmtree(w, True); shutil.rmtree(side, True)
sys.exit(1 if bad else 0)
