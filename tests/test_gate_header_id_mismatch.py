"""ESCAPE regression (c5x-rvttype 2026-11-14): a duplicate-type output whose new element HEADER carries another id than its record (1542917 -> 1542924; record and ElemTable row unchanged) was ACCEPTED by the gate. SaveGate RvtAdapter._header_ids must name it; the true output stays clean. Autodesk 2024 HVAC sample, skips if absent."""
import os, sys, subprocess, tempfile
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.expanduser('~/rvt-research/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(S): print('skip'); sys.exit(0)
sys.path[:0] = [os.path.expanduser('~/src/savegate'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')]
import savegate.adapters as A
src = open(S, 'rb').read(); W = tempfile.mkdtemp(); res = {}
for mut, tool in (('', 'rvt_dup_type_gen.py'), ('hdr_id', 'rvt_dup_type_mut.py'), ('no_et', 'rvt_dup_type_mut.py')):
    o = os.path.join(W, (mut or 'good') + '.rvt'); env = dict(os.environ, MUT=mut) if mut else os.environ
    r = subprocess.run([sys.executable, os.path.join(H, '..', 'tools', tool), S, o, '1379030', 'ZZT'], capture_output=True, text=True, env=env, timeout=1800); assert r.returncode == 0, r.stderr[-300:]
    res[mut or 'good'] = A.RvtAdapter._header_ids(None, (src, open(o, 'rb').read())); os.remove(o)
assert res['good'] == [], res['good']
assert res['hdr_id'] and 'different from their record' in res['hdr_id'][0][1], res['hdr_id']
assert res['no_et'] and 'no Global/ElemTable row' in res['no_et'][0][1], res['no_et']      # new records without ElemTable rows (reader derives its element set from the table, so the older checks never saw them)
print('ok: true dup-type output clean, wrong header id and orphan records named:', res['hdr_id'][0][1][:60])
