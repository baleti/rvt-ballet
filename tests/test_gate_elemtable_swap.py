"""c1x-rvtsave 210 regression (severity 1 class): a validly re-deflated Global/ElemTable with two 16-byte entries swapped (swapped element ids/offsets) in a delete output must be REFUSED, control accepted.
# RVT_TEST_TIMEOUT=3600 (slow on a loaded host). Uses tools/rvt_edit_flip.py EDIT_FLIP_ELEMTABLE_SWAP on the Autodesk 2024 HVAC sample."""
import os, sys, subprocess
SRC = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
env = dict(os.environ, RVTBALLET_ENABLE_DELETE='1', EDIT_FLIP_ELEMTABLE_SWAP='6')
r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_edit_flip.py'), SRC, '[{"op":"delete","eid":101016}]', '0', '9401'], capture_output=True, text=True, env=env, timeout=3400)
out = r.stdout
assert 'control_true_output ACCEPTED' in out, out[-800:] + r.stderr[-400:]
assert out.count('elemtable_swap_') >= 6 and 'no escapes' in out, out[-1500:]
print('OK elemtable swaps all refused')
