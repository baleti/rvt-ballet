"""c1x-rvtsave 215/217 regression (severity 1 class): on a MOVE output, (a) a validly re-deflated Global/ElemTable with two 16-byte entries swapped and (b) two chunks swapped inside the dirty partition member (valid re-encode) must be REFUSED, control accepted.
# RVT_TEST_TIMEOUT=3600 (slow on a loaded host). Uses tools/rvt_edit_flip.py EDIT_FLIP_ELEMTABLE_SWAP / EDIT_FLIP_MEMBERSWAP on the Autodesk 2024 HVAC sample."""
import os, sys, subprocess
SRC = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_edit_flip.py')
for var, tag, seed in (('EDIT_FLIP_ELEMTABLE_SWAP', 'elemtable_swap_', '9415'), ('EDIT_FLIP_MEMBERSWAP', 'memswap_', '9417')):
    env = dict(os.environ, **{var: '6'})
    r = subprocess.run([sys.executable, T, SRC, '[{"op":"move","eid":1366142,"dx":1,"dy":0,"dz":0}]', '0', seed], capture_output=True, text=True, env=env)
    out = r.stdout
    assert 'control_true_output ACCEPTED' in out, var + out[-800:] + r.stderr[-400:]
    assert out.count(tag) >= 6 and 'no escapes' in out, var + out[-1500:]
print('OK move-output swaps all refused')
