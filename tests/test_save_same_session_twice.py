"""Two in-place saves in the SAME session (no reload): the second must not be refused as 'changed on disk' by our own first save, bytes stay identical (identity); then an external change after the second save is still caught."""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import()
import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
try:
    src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h = sha(src)
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
    for i in range(3): save.save_overwrite(ss, 'm', src); assert sha(src) == h, 'save %d changed identity bytes' % i
    open(src, 'ab').write(b'x'); h2 = sha(src)
    try: save.save_overwrite(ss, 'm', src); raise SystemExit('FAIL: accepted over external change')
    except SystemExit: raise
    except Exception as e: print('external change refused:', type(e).__name__)
    assert sha(src) == h2
    print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
