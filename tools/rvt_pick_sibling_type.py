"""print 'PICK <instance eid> <its type eid> <sibling type eid>' for the first FamilyInstance whose family has another type (FamilySymbol.m_familyId equal). Read-only. usage: rvt_pick_sibling_type.py FILE.rvt"""
import sys, os, struct, collections
for lib in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(lib))
import rvtedit, rvt_geometry as G
src = sys.argv[1]; ed = rvtedit.Edit(src); ix = G.file_geometry_index(src)
def field(e, name):
    try:
        for l in ed.g.e.trace(e)[3]:
            if l[1] == name and l[3] - l[2] == 8: return struct.unpack_from('<Q', ed.g.bj, l[2])[0]
    except (struct.error, IndexError, KeyError): return None
fam = {s: field(s, 'FamilySymbol.m_familyId') for s, v in ix.items() if str(v) == 'FamilySymbol'}
by = collections.defaultdict(list)
for s, f in fam.items(): by[f].append(s)
for e, v in ix.items():
    if str(v) != 'FamilyInstance': continue
    s = field(e, 'FamilyInstance.m_masterSymbolId')
    if fam.get(s) is None: continue
    sib = [x for x in by.get(fam.get(s), []) if x != s]
    if sib: print('PICK', e, s, sib[0]); break
else: print('NONE')
