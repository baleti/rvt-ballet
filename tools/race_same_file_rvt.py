#!/usr/bin/env python3
"""race_same_file_rvt.py SRC [ROUNDS=2] : 4 processes each load the same private copy (same starting fingerprint), wait on a barrier file, then save_overwrite with a different Comments edit at the same instant. Exactly one must SAVE, the others refuse (lock/conflict); final file valid (reloads, the winner's edit reads back), no .sgtmp left. Exit 1 on any violation."""
import os, sys, shutil, tempfile, subprocess, time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = r'''
import os, sys, time, json
here, p, k, go = sys.argv[1:5]; k = int(k); sys.path.insert(0, here)
for q in (os.path.expanduser("~/rvt-research"), os.path.expanduser("~/rvt-research/write-lab")): sys.path.insert(0, q)
os.environ["RVTBALLET_EDIT_BACKEND"] = "rvtedit"
from rvtballet import save
import rvt_params
g = lambda x: (x.get("params", x) if isinstance(x, dict) else {})
els = [e for e, d in rvt_params.params(p).items() if g(d).get("Comments") == ""]
ss = save.SaveSessions(); ss.doc("m", p)
save.add_edit(ss, "m", p, {"op": "set_string", "eid": els[k], "param": "Comments", "value": "racer%d" % k})
while not os.path.exists(go): time.sleep(0.01)
try: save.save_overwrite(ss, "m", p); print("SAVED", els[k])
except BaseException as e: print("REFUSED", type(e).__name__)
'''
src = sys.argv[1]; rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 2; bad = 0
sys.path.insert(0, HERE)
for rnd in range(rounds):
    w = tempfile.mkdtemp(); side = tempfile.mkdtemp(); p = os.path.join(w, 'a' + os.path.splitext(src)[1]); shutil.copy(src, p); go = side + '/go'
    open(side + '/c.json', 'w').write('{"allow_overwrite": true}'); open(side + '/g.json', 'w').write('{"rvt": {"*": "open"}}')
    env = dict(os.environ, PYTHONPATH=os.path.expanduser('~/src/savegate'), SAVEGATE_JOURNAL=side + '/j', SAVEGATE_CACHE=side + '/c', DWG_BALLET_CONFIG=side + '/c.json', SAVEGATE_GATE=side + '/g.json', RVTBALLET_ALLOW_OVERWRITE='1')
    ps = [subprocess.Popen([sys.executable, '-c', CH, HERE, p, str(k), go], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for k in range(4)]
    time.sleep(45); open(go, 'w').write('1'); res = []
    for pr in ps:
        o, e = pr.communicate(timeout=1800); res.append((o.strip().splitlines() or ['CRASH ' + e[-120:]])[-1])
    saved = [r for r in res if r.startswith('SAVED')]; left = [f for f in os.listdir(w) if f.endswith('.sgtmp')]; ok = len(saved) == 1 and not left and all(r.split()[0] in ('SAVED', 'REFUSED') for r in res)
    if ok:
        import rvt_params
        eid = int(saved[0].split()[1]); k = int([i for i, r in enumerate(res) if r == saved[0]][0])
        try: got = (rvt_params.params(p)[eid] or {}); got = got.get('params', got).get('Comments'); ok = got == 'racer%d' % k
        except Exception as e: ok = False; print('reload failed', e)
    print('round', rnd, res, 'OK' if ok else 'BAD', flush=True); bad += not ok; shutil.rmtree(w, True); shutil.rmtree(side, True)
sys.exit(1 if bad else 0)
