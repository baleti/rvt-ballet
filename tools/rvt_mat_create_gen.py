"""CREATE a Material in a 2024 project by cloning an existing MaterialElem record of the same file (new id, new Name). Experiment, copy only.
usage: rvt_mat_create_gen.py SEED.rvt OUT.rvt SOURCE_MATERIAL_EID NEWNAME   (Autodesk samples / synthetic only)
Not Revit-verified. Shares the source's appearance/thermal asset references (no new asset elements are made)."""
import sys, struct, os, zlib
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); sys.path[:0] = [os.path.expanduser('~/rvt-research')]
os.environ['RVT_GEOM'] = '1'
import rvtgen
seed, out, mid, name = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
if os.path.realpath(seed) == os.path.realpath(out): sys.exit('REFUSED: output path equals the input file; this tool writes a copy only')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit as _ed
_ed._check_element_name(name)
import rvt_params, rvt_geometry as _G
_pr = rvt_params.params(seed); _ix = _G.file_geometry_index(seed)
if str(_ix.get(mid)) != 'MaterialElem': sys.exit('element %d is not a MaterialElem; nothing was written' % mid)
_P = lambda e: _pr.get(e, {}).get('params', _pr.get(e, {}))
for _e, _c in _ix.items():
    if str(_c) == 'MaterialElem' and _ed._nk(str(_P(_e).get('Name', ''))) == _ed._nk(name):
        sys.exit('material %d is already named %r: Revit does not allow duplicate material names; nothing was written' % (_e, name))
old = str(_P(mid).get('Name'))
g = rvtgen.Gen(seed); W = 8
T = g.template(mid)
hits = [(o, z) for n, o, z, v in T['log'] if n == 'Material.m_name' and v == old]
if len(hits) != 1: sys.exit('source material Name %r stored %d times as Material.m_name (need exactly 1); nothing was written' % (old, len(hits)))
nid = g.nextid; g.nextid += 1
print('old', mid, 'new', nid)
b = lambda x: struct.pack('<Q', x)
sub = lambda buf: bytes(buf).replace(b(mid), b(nid))
rec = bytearray(sub(T['rec'])); o, z = hits[0]
rec[o:z] = struct.pack('<I', len(name)) + name.encode('utf-16le')
rec = g.stamp(bytes(rec))
item = bytearray(sub(T['item'])); struct.pack_into('<I', item, 8, zlib.adler32(bytes(item[16:])) & 0xffffffff)
g.itag = T['item'][W + 8:W + 10]
g.new.append((sub(T['hdr']), rec, bytes(item), nid)); g.rows.append(sub(T['row']))
g.commit(out); print('ok', out)
