"""In-place save (atomic replace) must keep the source's permission bits, a hard-to-lose user xattr, and its inode owner; identity bytes. Documents what is NOT kept (inode)."""
import os, sys, tempfile, shutil, hashlib, subprocess, stat
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import()
import savegate as sg
try:
    for mode in (0o600, 0o640, 0o664, 0o644, 0o755):
        src = os.path.join(_T, 'src%o.rvt' % mode); shutil.copy(RTE, src); os.chmod(src, mode)
        xa = True
        try: os.setxattr(src, 'user.sgtest', b'keep')
        except OSError: xa = False
        st0 = os.stat(src)
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
        save.save_overwrite(ss, 'm', src); ss.close()
        st1 = os.stat(src)
        assert stat.S_IMODE(st1.st_mode) == mode, 'mode %o -> %o' % (mode, stat.S_IMODE(st1.st_mode))
        assert (st1.st_uid, st1.st_gid) == (st0.st_uid, st0.st_gid), 'owner changed'
        xk = (os.getxattr(src, 'user.sgtest') == b'keep') if xa else None
        print('mode %o kept; inode same=%s; xattr kept=%s' % (mode, st1.st_ino == st0.st_ino, xk))
        if xa: assert xk, 'user xattr lost by in-place save'
    print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
