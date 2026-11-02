"""determinism_rvt.py FILE.rfa|rvt... : the same rename (SymbolInfo.m_name) SAVE AS'd twice in fresh processes, and once with RVT_NOFAST=1 (pure Python), must give identical sha256 output bytes."""
import os, sys, subprocess, tempfile, hashlib
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CH = r'''
import sys, os, tempfile
sys.path.insert(0, sys.argv[1]); w = tempfile.mkdtemp(); open(w + "/g.json", "w").write('{"rvt": {"*": "open"}}')
os.environ.update(SAVEGATE_JOURNAL=w + "/j", SAVEGATE_CACHE=w + "/c", SAVEGATE_GATE=w + "/g.json")
from rvtballet import save
src, dst = sys.argv[2:4]; ss = save.SaveSessions()
save.add_edit(ss, "m1", src, {"op": "set_string", "eid": 0, "field": "SymbolInfo.m_name", "value": "Determinism ü"})
save.save_as(ss, "m1", src, dst); print("OK")
'''
bad = 0
for f in sys.argv[1:]:
    hs = []
    for mode in ('native', 'native', 'nofast'):
        d = tempfile.mkdtemp(); dst = os.path.join(d, 'o' + os.path.splitext(f)[1]); env = dict(os.environ)
        if mode == 'nofast': env['RVT_NOFAST'] = '1'
        r = subprocess.run([sys.executable, '-c', CH, HERE, f, dst], env=env, capture_output=True, text=True, timeout=900)
        hs.append(hashlib.sha256(open(dst, 'rb').read()).hexdigest()[:12] if os.path.exists(dst) else 'NOFILE ' + r.stderr[-80:])
    ok = len(set(hs)) == 1 and not hs[0].startswith('NOFILE'); bad += not ok
    print(os.path.basename(f)[-12:], hs, 'SAME' if ok else 'DIFF', flush=True)
sys.exit(1 if bad else 0)
