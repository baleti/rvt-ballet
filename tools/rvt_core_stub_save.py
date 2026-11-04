"""rvt_core_stub_save.py FILE.rfa|rvt : in-place SAVE (tools/save_real_overwrite.py flow, on a copy) must give the SAME bytes whether rvt_core is native, disabled (RVT_NOFAST=1) or replaced by a stub that fails: import-time ImportError, ImportError at attribute access (ABI mismatch), or RecDecoder.record raising mid-decode. A mode that crashes or differs is reported; exit 1 on any difference. Aggregate output, no paths."""
import os, sys, subprocess, tempfile, hashlib, shutil, json
HERE = os.path.dirname(os.path.abspath(__file__)); src = sys.argv[1]
STUBS = {'import_err': 'raise ImportError("compiled for another ABI")\n',
         'attr_err': 'def __getattr__(n):\n    raise ImportError("undefined symbol " + n)\n',
         'record_raises': 'class RecDecoder:\n    def __init__(s, *a, **k): pass\n    def set_es(s, v): pass\n    def set_strcap(s, v): pass\n    def record(s, *a, **k): raise RuntimeError("native record failed")\ndef parse_formats(*a, **k): raise RuntimeError("native parse failed")\n'}
LAUNCH = '''
import sys, os, runpy, importlib.util
f = os.environ.get("STUB_RVT_CORE")
if f:
    sp = importlib.util.spec_from_file_location("rvt_core", f); m = importlib.util.module_from_spec(sp); sys.modules["rvt_core"] = m
    try: sp.loader.exec_module(m)
    except ImportError: del sys.modules["rvt_core"]; sys.modules["rvt_core"] = None      # None in sys.modules makes `import rvt_core` raise ImportError
    sys.stderr.write("STUB-ACTIVE\\n")
sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name="__main__")
'''
T = tempfile.mkdtemp(); res = {}
for mode in ['native', 'nofast'] + list(STUBS):
    env = dict(os.environ); env.pop('RVT_NOFAST', None); out = os.path.join(T, mode + '.rvt')
    if mode == 'nofast': env['RVT_NOFAST'] = '1'
    elif mode != 'native':
        d = os.path.join(T, 'stub_' + mode); os.makedirs(d); open(d + '/stub_rvt_core.py', 'w').write(STUBS[mode]); env['STUB_RVT_CORE'] = d + '/stub_rvt_core.py'      # injected into sys.modules: the real rvt_core*.so sits on sys.path before any directory we could add
    env['KEEP_OUT'] = out
    p = subprocess.run([sys.executable, '-c', LAUNCH, os.path.join(HERE, 'save_real_overwrite.py'), os.path.join(T, mode + '.json'), src], env=env, capture_output=True, text=True, timeout=3000)
    r = 'NOOUT'
    if os.path.exists(out): r = hashlib.sha256(open(out, 'rb').read()).hexdigest()[:16]
    try: row = json.load(open(os.path.join(T, mode + '.json'))); r += ' ' + row.get('result', '?')
    except Exception: r += ' rc=%d %s' % (p.returncode, (p.stderr.strip().splitlines() or [''])[-1][:120]) + ('' if mode in ('native', 'nofast') or 'STUB-ACTIVE' in p.stderr else ' STUB-NOT-ACTIVE')
    res[mode] = r; print(mode, r, flush=True)
shutil.rmtree(T, True)
ok = len({v.split(' ')[0] for v in res.values()}) == 1 and all(v.endswith('OK') for v in res.values())
print('IDENTICAL' if ok else 'DIFF'); sys.exit(0 if ok else 1)
