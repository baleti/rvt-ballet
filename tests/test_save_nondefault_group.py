"""In-place SAVE! and RESTORE must keep a NON-default group (and setgid-free mode) of the source: shared-folder workflow. Skips if the user has no supplementary group."""
import os, sys, tempfile, shutil, stat, grp
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import()
import savegate as sg
try:
    other = [g for g in os.getgroups() if g != os.getgid()]
    if not other or not os.path.exists(RTE): print('skip'); sys.exit(0)
    g = other[0]; src = os.path.join(_T, 's.rvt'); shutil.copy(RTE, src); os.chown(src, -1, g); os.chmod(src, 0o664)
    st0 = os.stat(src); assert st0.st_gid == g
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
    save.save_overwrite(ss, 'm', src)
    st1 = os.stat(src)
    assert st1.st_gid == g, 'group %d -> %d after in-place save' % (g, st1.st_gid)
    assert stat.S_IMODE(st1.st_mode) == 0o664
    save.restore_backup(ss, 'm', src); ss.close(); st2 = os.stat(src)
    assert st2.st_gid == g, 'group lost by RESTORE'; assert stat.S_IMODE(st2.st_mode) == 0o664
    print('group %s kept after SAVE! and RESTORE' % grp.getgrgid(g).gr_name, 'OK')
finally: shutil.rmtree(_T, ignore_errors=True)
