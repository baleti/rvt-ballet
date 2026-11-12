"""c2x-rvtsave regression (severity 1): a one-byte flip within 32 B of the edit INSIDE a declared dirty member of a move output (outside the writer's own changed runs but inside the span window) (valid re-encode, so ECC/CRC are fine) used to be accepted by the gate.
Runs tools/rvt_edit_flip.py (delete of Viewport 101016 on the Autodesk 2024 HVAC sample, 4 in-member flips per dirty member, no random flips): the true output must be ACCEPTED (control) and every flip refused. Fails without member_pure_cut (savegate adapters + save._pending). Slow (minutes)."""
import os, sys, subprocess
SRC = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
env = dict(os.environ, EDIT_FLIP_WINDOW='2')
r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_edit_flip.py'), SRC, '[{"op":"move","eid":1366142,"dx":1,"dy":0,"dz":0}]', '0', '31'], capture_output=True, text=True, env=env, timeout=3000)
out = r.stdout
assert 'control_true_output ACCEPTED' in out, out[-800:] + r.stderr[-400:]
assert out.count('window_') >= 3 and 'no escapes' in out, out[-1500:]
print('OK move window flips all refused')
