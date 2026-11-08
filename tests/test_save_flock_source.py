"""Item 173: another process holds an flock (exclusive, then shared) on the source while we do an identity in-place save. Documents behaviour: allowed = refused with source untouched, or saved as identity; forbidden = source corrupted/partial."""
import os, sys, tempfile, shutil, hashlib, fcntl
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import()
import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
try:
    for mode in (fcntl.LOCK_EX, fcntl.LOCK_SH):
        src = os.path.join(_T, 'x.rte'); shutil.copy(RTE, src); h = sha(src)
        fd = os.open(src, os.O_RDONLY); fcntl.flock(fd, mode)
        try:
            ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src); save.save_overwrite(ss, 'm', src); ss.close(); out = 'saved'
        except Exception as e: out = 'refused: %s %s' % (type(e).__name__, str(e)[:150])
        fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)
        print('mode', 'EX' if mode == fcntl.LOCK_EX else 'SH', out, 'identity' if sha(src) == h else 'DIFFERS')
        assert sha(src) == h, 'source changed'
        assert not [f for f in os.listdir(_T) if f.endswith('.part') or f.startswith('x.rte.')], os.listdir(_T)
    print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
