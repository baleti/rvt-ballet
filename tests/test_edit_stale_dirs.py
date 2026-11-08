"""stale rvtballet-edit-* temp dirs (left by a killed edit) older than 6 h are swept; fresh ones and foreign-named dirs are kept."""
import os, sys, tempfile, time, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit
T = tempfile.mkdtemp(); tempfile.tempdir = T
old = os.path.join(T, 'rvtballet-edit-old'); new = os.path.join(T, 'rvtballet-edit-new'); other = os.path.join(T, 'other-old'); lnk = os.path.join(T, 'rvtballet-edit-link')
for d in (old, new, other): os.mkdir(d); open(os.path.join(d, 'in.rvt'), 'wb').write(b'x')
os.symlink(other, lnk); t = time.time() - 7 * 3600
for d in (old, other): os.utime(d, (t, t))
os.utime(lnk, (t, t), follow_symlinks=False)
n = edit._sweep_stale_edit_dirs()
assert n == 1 and not os.path.exists(old) and os.path.exists(new) and os.path.exists(other) and os.path.islink(lnk), (n, os.listdir(T))
shutil.rmtree(T); print('stale edit dirs swept OK')
