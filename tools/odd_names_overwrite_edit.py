"""[EDIT variant: a real element MOVE (eid 301595, 2024_writer_cols2 scene) is applied first, then SAVE! under each name; SAVED must write exactly the new bytes and keep a backup == original]
odd_names_overwrite.py FILE.rfa|rvt... : in-place SAVE! (rvtballet.save.save_overwrite, no edit) of a copy under hostile file names (spaces, quotes, unicode, emoji, leading dash, 200 chars, newline, tab, #%&;$, UPPER, leading dot, multi dot). Each must end SAVED (output identical to source or valid) or cleanly refused with the original byte-identical; no stray tmp/part/lock files beside the file (a .savegate backup folder is by design). One child process per name."""
import os, sys, shutil, tempfile, subprocess, hashlib
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = ['a b  c', "q'uote\"", 'münchen äö', '中文图', 'emoji\U0001F600', '-dash', 'x' * 200, 'new\nline', 'tab\tname', '#%25&;$', 'UPPER', '.hidden', 'a.b.c']
CHILD = r'''
import sys, os
sys.path.insert(0, sys.argv[1])
from rvtballet import save
from rvtballet import edit
ss = save.SaveSessions(); p = sys.argv[2]
try:
    d = ss.doc("m1", p); nb, _ = edit.apply_full(d.buf, [edit.validate_op({"op": "move", "eid": 301595, "dx": 1.0})])
    open(p + ".expect", "wb").write(nb)
    r = save.save_overwrite(ss, "m1", p, new_bytes=nb, manifest={"modified": ["el:301595"]}); print("SAVED", str(r.get("status", ""))[:20])
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
        env = dict(os.environ, SAVEGATE_GATE=side + '/g.json', SAVEGATE_JOURNAL=side + '/j', SAVEGATE_CACHE=side + '/c', RVTBALLET_ALLOW_OVERWRITE='1', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_LAYOUT_CHANGE='1')
        h0 = hashlib.sha256(open(p, 'rb').read()).hexdigest()
        r = subprocess.run([sys.executable, '-c', CHILD, HERE, p], capture_output=True, text=True, env=env, timeout=900)
        res = (r.stdout.strip().splitlines() or ['NOOUT ' + r.stderr[-80:]])[-1]
        same = hashlib.sha256(open(p, 'rb').read()).hexdigest() == h0
        exp = p + '.expect'; newok = os.path.exists(exp) and hashlib.sha256(open(p, 'rb').read()).hexdigest() == hashlib.sha256(open(exp, 'rb').read()).hexdigest()
        if os.path.exists(exp): os.remove(exp)
        left = sorted(x for x in os.listdir(w) if x != '.savegate'); bk = os.listdir(w + '/.savegate') if os.path.isdir(w + '/.savegate') else []
        bkok = all(hashlib.sha256(open(os.path.join(w, '.savegate', b), 'rb').read()).hexdigest() == h0 for b in bk if os.path.isfile(os.path.join(w, '.savegate', b)) and (b.startswith(nm) or len((nm + ext).encode()) > 200)) and (not res.startswith('SAVED') or any(b.startswith(nm) or len((nm + ext).encode()) > 200 for b in bk))
        ok = bkok and ((res.startswith('SAVED') and newok) or (res.startswith('RAISED') and same)) and left == [nm + ext] and all(b.startswith(nm) or len((nm + ext).encode()) > 200 for b in bk)
        print(os.path.basename(f)[:10], repr(nm[:14]), res[:80], 'same' if same else 'changed', 'OK' if ok else 'BAD ' + repr(left[:3] + bk[:2]), flush=True); bad += not ok
        shutil.rmtree(w, True); shutil.rmtree(side, True)
sys.exit(1 if bad else 0)
