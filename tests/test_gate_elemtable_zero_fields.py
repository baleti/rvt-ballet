"""ESCAPE regression (c5x-rvttype 2026-11-14): a duplicate-type output whose new ElemTable row has junk (0xEE) in the always-zero tail field (row bytes 36..39) was ACCEPTED by the gate. The ElemTable damage check must name it; the true output stays clean. Autodesk 2024 HVAC sample, skips if absent."""
import os, sys, subprocess, tempfile
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(S): print('skip'); sys.exit(0)
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
import cfb, savegate.adapters as A
fn = A._rvt_elemtable_damage; W = tempfile.mkdtemp(); res = {}
for mut, tool in (('', 'rvt_dup_type_gen.py'), ('row_junk', 'rvt_dup_type_mut.py')):
    o = os.path.join(W, (mut or 'good') + '.rvt'); env = dict(os.environ, MUT=mut) if mut else os.environ
    r = subprocess.run([sys.executable, os.path.join(H, '..', 'tools', tool), S, o, '1379030', 'ZZT'], capture_output=True, text=True, env=env, timeout=1800); assert r.returncode == 0, r.stderr[-300:]
    b = open(o, 'rb').read(); res[mut or 'good'] = fn(cfb.CFB(b).streams(), b); os.remove(o)
assert res['good'] == [], res['good']
assert res['row_junk'] and 'non-zero bytes' in res['row_junk'][0], res['row_junk']
print('ok: true dup-type output clean, junk in ElemTable row tail named:', res['row_junk'][0][:70])
