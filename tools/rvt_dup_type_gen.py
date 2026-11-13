"""DUPLICATE a FamilySymbol (type) of a 2024 project: clone symbol + its FamSymSurrogate with new ids and a new name (rung 4b).
usage: gen_dup_type.py SEED.rvt OUT.rvt SYMBOL_EID NEWNAME   (Autodesk samples / synthetic only)"""
import sys, struct, os; sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab'))
os.environ['RVT_GEOM'] = '1'
import rvtgen
seed, out, tid, name = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
def _refuse_crash(t, v, tb):   # only Revit 2024/2026 layouts are verified; any other file must fail cleanly with no output written
    try:
        if os.path.exists(out) and os.path.getsize(out) == 0: os.remove(out)
    except OSError: pass
    sys.exit('REFUSED: this file is not a layout the duplicate-type writer supports (%s: %s); nothing was written' % (t.__name__, v))
sys.excepthook = _refuse_crash
import os
if os.path.realpath(seed)==os.path.realpath(out): sys.exit('REFUSED: output path equals the input file; this tool writes a copy only')
# explicit year guard: the writer is verified on 2024 only; other years must be refused before any parsing
sys.path[:0] = [os.path.expanduser('~/rvt-research/write-lab')]
import re as _re, cfb as _cfb
try: _fy = int(_re.search(r'(20[12]\d)', bytes(_cfb.CFB(open(seed, 'rb').read()).streams()['BasicFileInfo'].data).decode('utf-16le', 'ignore')).group(1))
except Exception: sys.exit('REFUSED: cannot read the Revit version of the file; nothing written')
if _fy != 2024: sys.exit('REFUSED: duplicate type is only built for Revit 2024 files (this file is %d); nothing written' % _fy)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit as _ed
_ed._check_element_name(name)          # Revit's name rules (empty, forbidden chars, control/format chars)
sys.path[:0] = [os.path.expanduser('~/rvt-research')]
import rvt_params, rvt_geometry as _G
_pr = rvt_params.params(seed); _ix = _G.file_geometry_index(seed)
_P = lambda e: _pr.get(e, {}).get('params', _pr.get(e, {}))
_fam = _P(tid).get('Family Name')
if _ix.get(tid) != 'FamilySymbol': sys.exit('element %d is not a FamilySymbol; nothing was written' % tid)
for _e, _c in _ix.items():
    if str(_c) == 'FamilySymbol' and _P(_e).get('Family Name') == _fam and _ed._nk(str(_P(_e).get('Type Name', ''))) == _ed._nk(name):
        sys.exit('type %d of family %r is already named %r: Revit does not allow duplicate type names in a family; nothing was written' % (_e, _fam, name))
g = rvtgen.Gen(seed); e = g.e; W = 8
_pn = e.trace(tid)[0]
if _pn != g.pn:    # multi-partition files (Site 2024): templates and the new records must live in the partition that holds the symbol
    g = rvtgen.Gen(seed, _pn); e = g.e
assert e.trace(tid)[2]['class'] == 'FamilySymbol'
T = g.template(tid); L = {n: (o, z) for n, o, z, _ in T['log']}
sur = struct.unpack_from('<Q', T['rec'], L['FamilySymbol.m_partitionSurrogateId'][0])[0]
if not any(x[0] == g.pn for x in e.m.find(sur)):
    sys.exit('symbol %d and its surrogate %d live in different partitions (%s vs %s): a cross-partition duplicate is not supported; nothing was written' % (tid, sur, g.pn, [x[0] for x in e.m.find(sur)]))
assert e.trace(sur)[2]['class'] == 'FamSymSurrogate', e.trace(sur)[2]['class']
S = g.template(sur)
nid = g.nextid; g.nextid += 2; nsur = nid + 1
print('old', tid, sur, 'new', nid, nsur)
b = lambda x: struct.pack('<Q', x)
def sub(buf): return bytes(buf).replace(b(tid), b(nid)).replace(b(sur), b(nsur))
def mk(Tm, new_id, is_sym):
    rec = bytearray(sub(Tm['rec']))
    if is_sym:
        o, z = L['SymbolInfo.m_name']        # old offsets valid: ids are same length, name edited last
        nb = struct.pack('<I', len(name.encode('utf-16le')) // 2) + name.encode('utf-16le'); rec[o:z] = nb
    rec = bytearray(g.stamp(bytes(rec)))
    hdr = sub(Tm['hdr']); item = bytearray(sub(Tm['item'])); struct.pack_into('<I', item, 8, __import__('zlib').adler32(bytes(item[16:])) & 0xffffffff); item = bytes(item); row = bytearray(sub(Tm['row']))
    et = g._et(); n_ = struct.unpack_from('<I', et, 2)[0]
    return bytes(hdr), bytes(rec), bytes(item), bytes(row)
for Tm, i, is_sym in ((T, nid, True), (S, nsur, False)):
    hdr, rec, item, row = mk(Tm, i, is_sym)
    g.itag = Tm['item'][W + 8:W + 10]
    g.new.append((hdr, rec, item, i)); g.rows.append(row)
g.commit(out); print('ok', out)
