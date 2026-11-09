"""Source lives in a setgid directory whose group differs from the file's group: in-place SAVE! and RESTORE must keep the FILE's group (new inode must not inherit the directory group)."""
import os, sys, tempfile, shutil, stat
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import()
import savegate as sg
try:
    other = [g for g in os.getgroups() if g != os.getgid()]
    if not other or not os.path.exists(RTE): print('skip'); sys.exit(0)
    dg = other[0]; d = os.path.join(_T, 'sg'); os.makedirs(d); os.chown(d, -1, dg); os.chmod(d, 0o2775)
    assert os.stat(d).st_mode & stat.S_ISGID
    src = os.path.join(d, 's.rvt'); shutil.copy(RTE, src); fg = os.getgid(); os.chown(src, -1, fg); os.chmod(src, 0o664)
    os.chown(src, -1, fg); st0 = os.stat(src); assert st0.st_gid == fg, st0.st_gid
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
    save.save_overwrite(ss, 'm', src); g1 = os.stat(src).st_gid
    save.restore_backup(ss, 'm', src); ss.close(); g2 = os.stat(src).st_gid
    print('file group %d, dir group %d, after SAVE! %d, after RESTORE %d' % (fg, dg, g1, g2))
    assert g1 == fg, 'SAVE! changed file group to the directory group'
    assert g2 == fg, 'RESTORE changed file group'
    print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
