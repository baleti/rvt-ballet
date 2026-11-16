"""c1x-rvtmove 2026-11-16: opt-in co-move of Facades 2024 wall 802680 + its hosted window 802682 changes exactly the wall (GLine + planes) and the window with its 4 nested sub-components (Trf.m_or +1 ft), nothing else; without the opt-in env the wall move is refused."""
import os, sys, subprocess, tempfile, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
F = os.path.expanduser('~/rvt-research/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt')
if not (os.path.exists(LAB) and os.path.exists(F)): print('skip'); sys.exit(0)
import rvt_diff
d = tempfile.mkdtemp(); o = os.path.join(d, 'o.rvt')
env = dict(os.environ, RVTBALLET_MOVE_ANY='1', RVTEDIT_MOVE_WALL_DEPS='1', RVTEDIT_MOVE_WALL_TOUCH='1')
r = subprocess.run([sys.executable, LAB, F, o, 'mv:802680:1:0:0', 'mv:802682:1:0:0'], capture_output=True, text=True, cwd=os.path.dirname(LAB), env=env, timeout=1500)
assert os.path.exists(o), r.stderr[-400:]
rep = rvt_diff.pretty(rvt_diff.diff(F, o, True))
ids = sorted(int(m) for m in re.findall(r'^  id (\d+) ', rep, re.M))
assert ids == [802680, 802682, 802683, 802684, 802685, 802686], ids
assert 'added 0' in rep and 'removed 0' in rep, rep[:300]
# touch guard (default): Revit auto-joins neighbour 802687 on this move (wmp802680 witness), so the lab writer refuses without the force env
env2 = dict(env); env2.pop('RVTEDIT_MOVE_WALL_TOUCH'); o2 = os.path.join(d, 'o2.rvt')
r2 = subprocess.run([sys.executable, LAB, F, o2, 'mv:802680:1:0:0'], capture_output=True, text=True, cwd=os.path.dirname(LAB), env=env2, timeout=1500)
assert not os.path.exists(o2) and '802687' in (r2.stdout + r2.stderr), (r2.stdout + r2.stderr)[-400:]
# product path: the wall move is refused outright (no Revit-verified wall move); the lab backend's own dependents() guard is blind on this sample (returns [] even for wall 593220), so the product refusal is the protection
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit')
os.environ.pop('RVTBALLET_MOVE_ANY', None); os.environ.pop('RVTEDIT_MOVE_WALL_DEPS', None)
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
from rvtballet import save
import shutil, hashlib
src = os.path.join(_T, 's.rvt'); shutil.copy(F, src); h0 = hashlib.sha256(open(src, 'rb').read()).hexdigest()
ss = save.SaveSessions(); ss.doc('m', src)
for w in (802680, 593220):
    try: save.add_edit(ss, 'm', src, {'op': 'move', 'eid': w, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}); raise SystemExit('wall %d move accepted' % w)
    except (save.SaveError if hasattr(save, 'SaveError') else Exception) as e: assert 'SWall' in str(e) or 'refus' in str(e).lower(), str(e)[:200]
assert hashlib.sha256(open(src, 'rb').read()).hexdigest() == h0
print('wall 802680 co-move changes exactly wall + window + 4 nested; wall move refused by the product: OK')
