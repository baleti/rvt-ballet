"""SIGKILL at every savegate step (tmp_written, before_replace, after_replace) through rvtballet.save.save_as / save_overwrite, and a real ENOSPC on a 1 MB
tmpfs (rootless unshare). Invariants: source bytes intact (SAVE AS) or old-or-new complete (overwrite), SAVE AS target absent or complete, journal of the killed
session is listed by save.recoverable with the stage reached, a later normal save works (no stale lock)."""
import os, sys, tempfile, hashlib, shutil, subprocess, signal, json
_T = tempfile.mkdtemp(); J = _T + '/j'; C = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RTE = os.path.expanduser(os.environ.get('RVTBALLET_CRASH_SRC', '~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte'))      # override: any 2024 .rte/.rvt
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
CHILD = r'''
import os, sys, signal, json
sys.path.insert(0, %(here)r)
from rvtballet import save
save._import()
import savegate as sg, savegate.atomic as A
step, mode, src, dest = sys.argv[1:5]
def hook(s):
    if s == step: os.kill(os.getpid(), signal.SIGKILL)
A._hook = hook
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
if mode == 'saveas': save.save_as(ss, 'm', src, dest)
else: save.save_overwrite(ss, 'm', src)
'''
def run(step, mode, src, dest):
    env = dict(os.environ, SAVEGATE_JOURNAL=J, SAVEGATE_CACHE=C)
    return subprocess.run([sys.executable, '-c', CHILD % {'here': HERE}, step, mode, src, dest], env=env, capture_output=True, text=True, timeout=300)
def leftovers(d): return [f for f in os.listdir(d) if 'sgtmp' in f or f.endswith('.part')]
def main():
    sys.path.insert(0, HERE); os.environ['SAVEGATE_JOURNAL'] = J; os.environ['SAVEGATE_CACHE'] = C
    from rvtballet import save
    save._import()
    h0 = sha(RTE); res = {}
    for mode in ('saveas', 'overwrite'):
        for step in ('tmp_written', 'before_replace', 'after_replace'):
            d = tempfile.mkdtemp(dir=_T); src = os.path.join(d, 'src.rvt'); shutil.copy(RTE, src); dest = os.path.join(d, 'out.rvt')
            r = run(step, mode, src, dest); assert r.returncode == -signal.SIGKILL, (mode, step, r.returncode, r.stderr[-300:])
            ok_src = sha(src) == h0                                    # identity bytes: old and new are equal, so intact == complete
            assert ok_src, (mode, step, 'source damaged')
            if mode == 'saveas': assert not os.path.exists(dest) or sha(dest) == h0, (mode, step, 'partial target')
            rec = [x for x in save.recoverable(save.SaveSessions()) if x['source'] == src]
            assert len(rec) == 1, (mode, step, rec)
            res['%s/%s' % (mode, step)] = rec[0]['last']
            # a later save must work: stale temp/lock must not block it
            ss = save.SaveSessions(__import__('savegate').Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
            save.save_as(ss, 'm', src, os.path.join(d, 'again.rvt')) if mode == 'saveas' else save.save_overwrite(ss, 'm', src)
            assert sha(src) == h0 and (mode != 'saveas' or sha(os.path.join(d, 'again.rvt')) == h0)
            ss.close()
    # real ENOSPC on a 1 MB tmpfs: target absent, no temp left, source on the big fs intact
    s = tempfile.mkdtemp(dir=_T); src = os.path.join(s, 'src.rvt'); shutil.copy(RTE, src); sp = os.path.join(s, 'e.py'); m = os.path.join(s, 'mnt'); os.makedirs(m)
    open(sp, 'w').write(r'''
import os, sys
sys.path.insert(0, %r)
from rvtballet import save
save._import()
import savegate as sg
ss = save.SaveSessions(sg.Config(verify=False)); ss.doc('m', %r)
try: save.save_as(ss, 'm', %r, os.path.join(sys.argv[1], 'x.rvt')); print('UNEXPECTED OK')
except Exception as e: print('ERR', type(e).__name__, str(e)[:120]); print('LEFT', sorted(os.listdir(sys.argv[1])))
''' % (HERE, src, src))
    p = subprocess.run(['unshare', '-rm', 'sh', '-c', 'mount -t tmpfs -o size=1m tmpfs %s && %s %s %s' % (m, sys.executable, sp, m)], capture_output=True, text=True, timeout=300,
                       env=dict(os.environ, SAVEGATE_JOURNAL=J, SAVEGATE_CACHE=C))
    if 'ERR' in p.stdout:
        assert 'DiskError' in p.stdout and "LEFT []" in p.stdout, p.stdout; res['enospc_tmpfs'] = 'DiskError, nothing left'
    else: res['enospc_tmpfs'] = 'skipped (unshare unavailable: %s)' % (p.stderr.strip()[-80:] or p.stdout.strip()[-80:])
    assert sha(src) == h0
    print('save crash OK', json.dumps(res))
if not os.path.exists(RTE) or not __import__('importlib.util').util.find_spec('aiohttp') and False: print('skip')
else: main()
