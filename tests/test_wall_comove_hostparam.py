"""c1x-rvtmove 2026-11-16: moving a host wall together with its hosted window in ONE edit (wall op first) keeps the window's InsertableInst.m_hostParam unchanged (Revit-made move of Facades 2024 wall 593220 does the same; hostParam is the distance along the host, which moved too) and moves Trf.m_or by the displacement. Moving the window alone still shifts hostParam along the wall. Synthetic scene 2024_writer_hosted2 (wall 301557 hosts instance 301559); skipped without it."""
import os, sys, subprocess, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
LAB = os.path.expanduser('~/rvt-research/edit-lab/rvtedit.py')
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_hosted2.rte')
if not (os.path.exists(LAB) and os.path.exists(F)): print('skip'); sys.exit(0)
import rvt_diff
def run(*ops):
    o = os.path.join(tempfile.mkdtemp(), 'o.rte')
    env = dict(os.environ, RVTBALLET_MOVE_ANY='1', RVTEDIT_MOVE_WALL_DEPS='1')
    r = subprocess.run([sys.executable, LAB, F, o] + list(ops), capture_output=True, text=True, cwd=os.path.dirname(LAB), env=env)
    assert os.path.exists(o), r.stderr[-400:]
    rep = rvt_diff.pretty(rvt_diff.diff(F, o, True)); return [l for l in rep.split('\n') if 'hostParam' in l or 'Trf.m_or' in l]
both = run('mv:301557:0:1:0', 'mv:301559:0:1:0')
alone = run('mv:301559:0:1:0')
assert not any('hostParam' in l for l in both), both
assert any('hostParam' in l for l in alone), alone
assert any('Trf.m_or' in l for l in both), both
print('wall+window co-move keeps hostParam, lone window move shifts it: OK')
# item 62: without the opt-in env the host wall move is refused and nothing is written
o = os.path.join(tempfile.mkdtemp(), 'o.rte'); env = dict(os.environ, RVTBALLET_MOVE_ANY='1'); env.pop('RVTEDIT_MOVE_WALL_DEPS', None)
r = subprocess.run([sys.executable, LAB, F, o, 'mv:301557:0:1:0'], capture_output=True, text=True, cwd=os.path.dirname(LAB), env=env)
assert not os.path.exists(o) and 'refused' in (r.stderr + r.stdout).lower(), (r.stdout[-200:], r.stderr[-200:])
print('hosting wall move refused without opt-in: OK')
