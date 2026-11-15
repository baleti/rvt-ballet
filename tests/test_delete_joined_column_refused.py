"""c1x-rvtdel: Snowdon Facades 2024 Columns 593361 / 593363 are joined to 2 elements each. Deleting 593361 alone was accepted by SAVE AS but the output failed to open in the Revit 2024 VM
(CorruptModelException 'needs to be recovered', 2026-11-15). SAVE AS (the real server route) must now refuse it and write nothing. Fails without the jd check in save.group_warning."""
import os, sys, subprocess, tempfile, shutil
SRC = os.path.expanduser('~/rvt-research/corpus/2024/46_Snowdon_Towers_Sample_Facades.rvt')
if not os.path.exists(SRC): print('skip'); sys.exit(0)
T = tempfile.mkdtemp()
try:
    env = dict(os.environ, SWEEP_EIDS='593361,593363', SWEEP_CLASSES='FamilyInstance', TMPDIR=T)
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'rvt_delete_sweep.py'), T + '/o.json', SRC, '2'], env=env, capture_output=True, text=True, timeout=3400)
    out = r.stdout; rows = [l for l in out.splitlines() if l.startswith('ROW')]; print('\n'.join(rows)); print(out[-300:] if not rows else '')
    if not rows or any('ACCEPTED' in l for l in rows): raise SystemExit('FAIL joined column delete accepted (or no rows): ' + out[-300:])
    print('PASS')
finally: shutil.rmtree(T, ignore_errors=True)
