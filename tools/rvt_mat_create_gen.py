"""CREATE a Material in a 2024 project by cloning an existing MaterialElem record of the same file (new id, new Name). Experiment, copy only.
usage: rvt_mat_create_gen.py SEED.rvt OUT.rvt SOURCE_MATERIAL_EID NEWNAME   (Autodesk samples / synthetic only)
Not Revit-verified. Shares the source's appearance/thermal asset references (no new asset elements are made)."""
import sys, struct, os, zlib
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); sys.path[:0] = [os.path.expanduser('~/rvt-research')]
os.environ['RVT_GEOM'] = '1'
import rvtgen
seed, out, mid, name = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
def _refuse_crash(t, v, tb):   # only Revit 2024/2026 layouts are verified; any other file must fail cleanly with no output written
    try:
        if os.path.exists(out) and os.path.getsize(out) == 0: os.remove(out)
    except OSError: pass
    sys.exit('REFUSED: this file is not a layout the material-create writer supports (%s: %s); nothing was written' % (t.__name__, v))
sys.excepthook = _refuse_crash
if os.path.realpath(seed) == os.path.realpath(out): sys.exit('REFUSED: output path equals the input file; this tool writes a copy only')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import re as _re
sys.path[:0] = [os.path.expanduser('~/rvt-research')]
import cfb as _cfb
try: _fy = int(_re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(seed, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
except Exception: sys.exit('REFUSED: cannot read the Revit version of the file; nothing was written')
if _fy not in (2024, 2026): sys.exit('REFUSED: material create is only built for Revit 2024/2026 files (this file is %d); nothing was written' % _fy)
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
rec[o:z] = struct.pack('<I', len(name.encode('utf-16le')) // 2) + name.encode('utf-16le')
rec = g.stamp(bytes(rec))
item = bytearray(sub(T['item'])); struct.pack_into('<I', item, 8, zlib.adler32(bytes(item[16:])) & 0xffffffff)
g.itag = T['item'][W + 8:W + 10]
g.new.append((sub(T['hdr']), rec, bytes(item), nid)); g.rows.append(sub(T['row']))
# Revit also registers the new material in Global/Latest: u32 count + that many ascending 8-byte MaterialElem ids (+ ffff.. terminator); paired Revit experiment c5xmat: count 56 -> 57, new id appended at the end
_mids = sorted(e for e, c in _ix.items() if str(c) == 'MaterialElem')
def _latest_add(raw, _mids=_mids, nid=nid):
    pat = struct.pack('<I', len(_mids)) + b''.join(struct.pack('<Q', m) for m in _mids) + b'\xff' * 8
    k = raw.find(pat)
    if k < 0 or raw.find(pat, k + 1) >= 0: raise SystemExit('REFUSED: the Global/Latest material registry was not found exactly once (found at %d); nothing was written' % k)
    if nid <= _mids[-1]: raise SystemExit('REFUSED: new id is not above all material ids; nothing was written')
    e = k + 4 + 8 * len(_mids)
    return raw[:k] + struct.pack('<I', len(_mids) + 1) + raw[k + 4:e] + struct.pack('<Q', nid) + raw[e:]
g.latest_edits = getattr(g, 'latest_edits', []) + [(0, _latest_add)]
g.commit(out); print('ok', out)
