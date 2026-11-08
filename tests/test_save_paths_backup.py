"""(a) in-place save with an unwritable backup location (SAVEGATE_BACKUPS=cache, cache dir 0555): must refuse before replacing, source identical.
(b) in-place save of sources whose path has spaces, unicode, a 200-char name and a deep directory: works (identity) with source intact, or refuses cleanly; never damage."""
import os, sys, tempfile, shutil, hashlib, subprocess
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
T = tempfile.mkdtemp()
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
CHILD = r'''
import os, sys
sys.path.insert(0, %r)
from rvtballet import save
save._import()
import savegate as sg
src = sys.argv[1]
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
try: save.save_overwrite(ss, 'm', src); print('RESULT OK')
except Exception as e: print('RESULT ERR', type(e).__name__, str(e)[:100])
'''
def run(src, cache, backups=None):
    env = dict(os.environ, SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=cache)
    if backups: env['SAVEGATE_BACKUPS'] = backups
    p = subprocess.run([sys.executable, '-c', CHILD % HERE, src], capture_output=True, text=True, timeout=600, env=env)
    return [l for l in p.stdout.splitlines() if l.startswith('RESULT')] or ['NO RESULT ' + p.stderr[-200:]]
try:
    h0 = sha(RTE)
    # (a)
    d = T + '/a'; os.makedirs(d); src = d + '/src.rvt'; shutil.copy(RTE, src); c = T + '/ro'; os.makedirs(c); os.chmod(c, 0o555)
    r = run(src, c, 'cache'); print('unwritable backup:', r); os.chmod(c, 0o755)
    assert sha(src) == h0 and 'RESULT OK' not in r[0], 'unwritable backup dir: file damaged or save accepted without a backup'
    assert 'NO RESULT' not in r[0], r
    assert os.listdir(d) == ['src.rvt'], os.listdir(d)
    # (b)
    deep = os.path.join(T, *['d%02d' % i for i in range(12)], 'ü mlaut ñ 日本語 dir')
    names = {'spaces': 'my model  v2 (final).rvt', 'unicode': 'Gebäude_Ünïcode_日本語_🏗.rvt', 'long200': 'n' * 196 + '.rvt'}
    for k, n in names.items():
        dd = deep if k != 'spaces' else T + '/sp ace'; os.makedirs(dd, exist_ok=True); src = os.path.join(dd, n); shutil.copy(RTE, src)
        r = run(src, T + '/c_' + k); print(k, r)
        assert 'NO RESULT' not in r[0], r
        assert sha(src) == h0, k + ': source changed by an identity save'
        assert not [f for f in os.listdir(dd) if 'sgtmp' in f or f.endswith('.part')], k + ' leftover'
    print('OK')
finally: shutil.rmtree(T, ignore_errors=True)
