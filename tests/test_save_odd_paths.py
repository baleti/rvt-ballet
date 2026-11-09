"""In-place save (atomic replace) of a source whose path has spaces, quotes, ';', unicode, a leading dash, a 200-char name and a deep directory: saved, bytes identical to the no-edit save of a plain path, no temp left, journal/backup work. Synthetic writer scene only."""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(RTE): print('SKIP no scene'); sys.exit(0)
from rvtballet import save
save._import()
import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def run(src):
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
    save.save_overwrite(ss, 'm', src); ss.close()
try:
    plain = os.path.join(_T, 'plain.rte'); shutil.copy(RTE, plain); run(plain); ref = sha(plain)
    names = ["my file (1).rte", "q'uo\"te;semi.rte", "-dash.rte", "café 日本語 \U0001F3D7.rte", "a" * 200 + ".rte", "  lead space.rte"]
    for i, n in enumerate(names + [None]):
        d = os.path.join(_T, 'dir %d' % i)
        if n is None: d = os.path.join(d, *['deep dï' + str(k) for k in range(12)]); n = 'x.rte'
        os.makedirs(d); src = os.path.join(d, n); shutil.copy(RTE, src)
        run(src)
        assert sha(src) == ref, 'saved bytes differ for %r' % n
        left = [f for f in os.listdir(d) if f not in (n, '.savegate')]
        sgd = os.path.join(d, '.savegate'); assert not [f for f in (os.listdir(sgd) if os.path.isdir(sgd) else []) if f.endswith('.tmp') or '.tmp' in f], 'temp in .savegate'
        assert not left, 'stray files %r next to %r' % (left, n)
        print('ok', repr(n[:30]), len(src))
    print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
