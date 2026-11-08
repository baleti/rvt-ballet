"""regression (c1x-rvttype): duplicate a type twice in a row (dup of dup output): ids do not collide, both names present, element count +2 each time; a third dup reusing the first new name is refused and writes nothing. Autodesk HVAC 2024 sample; slow (minutes); skips if absent."""
import glob, os, subprocess, sys, tempfile
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = sorted(glob.glob(os.path.expanduser('~/rvt-research/corpus/2024/*HVAC.rvt')))
if not F: print('skip: sample absent'); sys.exit(0)
T = os.path.join(H, 'tools', 'rvt_dup_type_gen.py'); d = tempfile.mkdtemp()
def run(i, o, n): return subprocess.run([sys.executable, T, i, d + '/' + o, '1379030', n], capture_output=True, text=True).returncode
if run(F[0], "a.rvt", "DUPA"): sys.exit("first dup failed")
assert subprocess.run([sys.executable, T, d + '/a.rvt', d + '/b.rvt', '1379030', 'DUPB']).returncode == 0
assert subprocess.run([sys.executable, T, d + '/b.rvt', d + '/c.rvt', '1379030', 'DUPA']).returncode != 0 and not os.path.exists(d + '/c.rvt')
sys.path[:0] = [os.path.expanduser('~/rvt-research'), H]
import rvt_geometry as G, rvt_params
n0 = len(G.file_geometry_index(F[0])); ix = G.file_geometry_index(d + '/b.rvt'); assert len(ix) == n0 + 4 and len(set(ix)) == len(ix)
pr = rvt_params.params(d + '/b.rvt'); names = sorted(str(p.get('params', p).get('Type Name')) for p in pr.values() if str(p.get('params', p).get('Type Name', '')).startswith('DUP'))
assert names == ['DUPA', 'DUPB'], names
print('ok: chained dup-type, unique ids, duplicate name refused')
