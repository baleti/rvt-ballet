"""RESTORE killed (SIGKILL / SIGTERM) at several moments: the target is then the saved state or the original, never partial; if the target is still the saved state the ORIGINAL bytes must remain recoverable (target or a backup copy); which backup index holds them after a killed restore is reported, not asserted. Synthetic cols2 .rte; scratch under ~/c3x-tmp-c4x (skips without the sample)."""
import os, sys, shutil, hashlib, subprocess, signal, time, tempfile
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RTE = os.path.expanduser('~/c2x-cols2.rte')
if not os.path.exists(RTE): print('skip'); sys.exit(0)
PRE = r'''
import os, sys, hashlib
sys.path.insert(0, %r)
os.environ['SAVEGATE_JOURNAL'] = %r; os.environ['SAVEGATE_CACHE'] = %r; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import save, edit
save._import()
import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
d = sys.argv[1]; src = os.path.join(d, 'src.rte')
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False))
'''
SETUP = PRE + r'''
import shutil
shutil.copy(%r, src); h0 = sha(src); dd = ss.doc('m', src)
nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
save.save_overwrite(ss, 'm', src, new_bytes=nb, manifest={'modified': ['el:301595']}); print('H0', h0, 'HS', sha(src))
'''
REST = PRE + r'''
save.restore_backup(ss, 'm', src, 0); print('RESTORED', sha(src))
'''
base = os.path.expanduser('~/c3x-tmp-c4x'); os.makedirs(base, exist_ok=True); T = tempfile.mkdtemp(dir=base); fails = []
try:
    S0 = T + '/snap'; os.makedirs(S0)
    code = (PRE % (os.path.abspath(HERE), S0 + '/j', S0 + '/c')) + (SETUP[len(PRE):] % (RTE,))
    r = subprocess.run([sys.executable, '-c', code, S0], capture_output=True, text=True, timeout=1200); out = r.stdout + r.stderr
    assert r.returncode == 0 and 'H0' in out, out[-300:]
    h0, hs = out.split('H0')[1].split()[:1][0], out.split('HS')[1].split()[0]
    for sig in (signal.SIGKILL, signal.SIGTERM):
        for delay in (0.0, 0.05, 0.1, 0.12, 0.14, 0.15, 0.16, 0.18, 0.2, 0.3):
            tag = '%s_%g' % (sig.name, delay); D = T + '/' + tag; shutil.copytree(S0, D)
            code = (PRE % (os.path.abspath(HERE), D + '/j', D + '/c')) + REST[len(PRE):]
            p = subprocess.Popen([sys.executable, '-c', code, D], stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            time.sleep(delay)
            try: os.killpg(p.pid, sig)
            except ProcessLookupError: pass
            p.wait(timeout=300); h = hashlib.sha256(open(D + '/src.rte', 'rb').read()).hexdigest()
            state = 'original' if h == h0 else 'saved' if h == hs else 'OTHER'
            bk = {}      # every backup copy still on disk (beside the file and in the cache), by sha
            for root in (D + '/.savegate', D + '/c'):
                for dp, _, fs in os.walk(root):
                    for f in fs:
                        try: bk[hashlib.sha256(open(os.path.join(dp, f), 'rb').read()).hexdigest()] = f
                        except OSError: pass
            recoverable = h == h0 or h0 in bk      # the ORIGINAL bytes must still exist somewhere after a killed restore
            if state == 'saved':
                r2 = subprocess.run([sys.executable, '-c', code, D], capture_output=True, text=True, timeout=300); h2 = hashlib.sha256(open(D + '/src.rte', 'rb').read()).hexdigest()
                print(tag, 'after kill: saved | original still in backups:', h0 in bk, '| second restore ->', 'original' if h2 == h0 else 'saved (index 0 is now the saved copy)')
            else: print(tag, 'after kill: original (restore had completed) | original in backups:', h0 in bk)
            if state == 'OTHER' or not recoverable: fails.append((tag, state, 'original unrecoverable', sorted(bk.values())))
    assert not fails, fails
    print('killed restore ok')
finally: shutil.rmtree(T, ignore_errors=True)
