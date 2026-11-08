"""c1x-rvtsave 212: loading a document (savegate open_doc) removes a >1h old crashed-save temp of ANY document in the folder, keeps a young one (maybe a live save of another file), and the next save of the file removes its own young orphan temp. Synthetic 2024 .rte."""
import os, sys, tempfile, shutil, time
T = tempfile.mkdtemp()
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.expanduser('~/src/savegate'))
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
from rvtballet import save
from savegate import atomic
d = tempfile.mkdtemp(dir=T); src = d + '/m.rvt'; shutil.copy(S, src)
other = d + '/.other.rvt.aaaaaa.zzz.sgtmp'; young_other = d + '/.other2.rvt.bbbbbb.yyy.sgtmp'
for p, age in ((other, 7200), (young_other, 10)):
    open(p, 'wb').write(b'junk'); t = time.time() - age; os.utime(p, (t, t))
own = d + '/' + atomic._temp_prefix(src) + 'orph1.sgtmp'; open(own, 'wb').write(b'junk')
ss = save.SaveSessions(__import__('savegate').Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
assert not os.path.exists(other), 'old foreign temp not swept at load'
assert os.path.exists(young_other), 'young foreign temp removed'
assert os.path.exists(own), 'own orphan removed too early (before any save)'
save.save_overwrite(ss, 'm', src)
assert not os.path.exists(own), 'own orphan temp survived a save'
assert os.path.exists(young_other)
print('OK: load sweeps old foreign temp, keeps young one; save removes own orphan')
