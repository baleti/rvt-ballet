"""c2x-rvtsave regression (severity 1): a one-byte flip on a byte the writer itself changed inside a declared dirty member of a SET_STRING (equal-length Mark) output (outside member_diff_ranges was already refused; flips inside the writer runs passed until member_raw_sha256). Autodesk 2024 HVAC sample, window flips, control accepted, all flips refused."""
import os, sys, subprocess
SRC = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
env = dict(os.environ, EDIT_FLIP_WINDOW='3')
r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_edit_flip.py'), SRC, '[{"op":"set_string","eid":1362429,"param":"Mark","value":"7","match":"1"}]', '0', '51'], capture_output=True, text=True, env=env, timeout=3000)
out = r.stdout
assert 'control_true_output ACCEPTED' in out, out[-800:] + r.stderr[-400:]
assert out.count('window_') >= 3 and 'no escapes' in out, out[-1500:]
print('OK set_string window flips all refused (member_raw_sha256)')
