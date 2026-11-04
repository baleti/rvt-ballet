#!/usr/bin/env python3
"""stale_eid_save_rvt.py FILE : save_overwrite with edits on hostile element ids (nonexistent, 0, -1, 2**70, bool, str, None, an id that exists but is not a parametric element) for set_string and move, in a child process per case. Must be: refused at add_edit/save with the file byte-identical, or saved and still a reloadable file. Exit 1 on a changed original after refusal, a crash, or an unreloadable save."""
import os, sys, shutil, tempfile, hashlib, subprocess
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = r'''
import sys, os
here, p, case = sys.argv[1:4]; sys.path.insert(0, here)
for q in (os.path.expanduser("~/rvt-research"), os.path.expanduser("~/rvt-research/write-lab")): sys.path.insert(0, q)
os.environ["RVTBALLET_EDIT_BACKEND"] = "rvtedit"
from rvtballet import save
eid = eval(case.split("|")[0]); kind = case.split("|")[1]
ss = save.SaveSessions(); ss.doc("m", p)
try:
    op = {"op": "set_string", "eid": eid, "param": "Comments", "value": "x"} if kind == "str" else {"op": "move", "eid": eid, "dx": 1.0, "dy": 0.0, "dz": 0.0}
    save.add_edit(ss, "m", p, op)
except BaseException as e: print("REFUSED-ADD", type(e).__name__); raise SystemExit
try: save.save_overwrite(ss, "m", p); print("SAVED")
except BaseException as e: print("REFUSED", type(e).__name__)
'''
f = sys.argv[1]; bad = 0; sha = lambda b: hashlib.sha256(b).hexdigest()[:10]
cases = ['99999999|str', '0|str', '-1|str', '2**70|str', 'True|str', '"abc"|str', 'None|str', '99999999|move', '0|move', '-1|move', '2**70|move', 'True|move']
for c in cases:
    w = tempfile.mkdtemp(); side = tempfile.mkdtemp(); p = os.path.join(w, 'a' + os.path.splitext(f)[1]); shutil.copy(f, p); orig = open(p, 'rb').read()
    open(side + '/c.json', 'w').write('{"allow_overwrite": true}'); open(side + '/g.json', 'w').write('{"rvt": {"*": "open"}}')
    env = dict(os.environ, PYTHONPATH=os.path.expanduser('~/src/savegate'), SAVEGATE_JOURNAL=side + '/j', SAVEGATE_CACHE=side + '/c', DWG_BALLET_CONFIG=side + '/c.json', SAVEGATE_GATE=side + '/g.json', RVTBALLET_ALLOW_OVERWRITE='1')
    r = subprocess.run([sys.executable, '-c', CH, HERE, p, c], env=env, capture_output=True, text=True, timeout=1800)
    res = (r.stdout.strip().splitlines() or ['CRASH ' + r.stderr[-100:]])[-1]; now = open(p, 'rb').read()
    ok = res.startswith('REFUSED') and now == orig or (res == 'SAVED' and now != orig and now[:8] == orig[:8])
    if res == 'SAVED':
        try:
            sys.path.insert(0, HERE); [sys.path.insert(0, os.path.expanduser(q)) for q in ('~/rvt-research',)]
            import rvt_params; rvt_params.params(p)
        except Exception as e: ok = False; res += ' UNRELOADABLE %s' % e
    print(c, res, 'OK' if ok else 'BAD', flush=True); bad += not ok; shutil.rmtree(w, True); shutil.rmtree(side, True)
sys.exit(1 if bad else 0)
