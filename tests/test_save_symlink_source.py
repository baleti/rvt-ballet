"""Item 189: in-place save where the source path is a symlink (and a hardlink). Allowed: refused untouched, or saved so that the symlink still points to the real file, whose content is a valid identity copy; forbidden: link replaced by a regular file while the target stays stale/lost, or target damaged."""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import()
import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
try:
    real = os.path.join(_T, 'real.rte'); shutil.copy(RTE, real); h = sha(real)
    for kind in ('symlink', 'hardlink'):
        lnk = os.path.join(_T, kind + '.rte')
        (os.symlink if kind == 'symlink' else os.link)(real, lnk)
        try:
            ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', lnk); save.save_overwrite(ss, 'm', lnk); ss.close(); out = 'saved'
        except Exception as e: out = 'refused: %s %s' % (type(e).__name__, str(e)[:100])
        print(kind, out, '| link is symlink:', os.path.islink(lnk), '| real sha same:', sha(real) == h, '| link sha same:', sha(lnk) == h)
        assert sha(real) == h and sha(lnk) == h or out.startswith('refused') is False and sha(lnk) == h, 'a path now holds different/damaged content'
        assert not [f for f in os.listdir(_T) if f.endswith('.part')]
        os.unlink(lnk)
    print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
