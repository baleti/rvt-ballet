"""c1x-rvtsave 213: a symlink named like a stale temp (old '.x.sgtmp' -> victim file elsewhere) planted in the folder must not make load/save delete or write the victim: only the link may be removed. Synthetic 2024 .rte."""
import os, sys, tempfile, shutil, time, hashlib
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
victim = T + '/victim.txt'; open(victim, 'wb').write(b'precious'); vh = hashlib.sha256(b'precious').hexdigest()
lnk_old = d + '/.evil.aaaaaa.zzz.sgtmp'; os.symlink(victim, lnk_old)
os.utime(lnk_old, (time.time() - 7200,) * 2, follow_symlinks=False)
own = d + '/' + atomic._temp_prefix(src) + 'orph1.sgtmp'; os.symlink(victim, own)
ss = save.SaveSessions(__import__('savegate').Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
save.save_overwrite(ss, 'm', src)
assert os.path.exists(victim) and hashlib.sha256(open(victim, 'rb').read()).hexdigest() == vh, 'victim touched through a planted symlink'
assert not os.path.lexists(own), 'own symlink orphan not removed'
print('OK: victim intact; old-link %s, own-link removed' % ('removed' if not os.path.lexists(lnk_old) else 'left'))
