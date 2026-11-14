"""LAB TOOL (c5x-rvttype): list FamilySymbols that hold a positive element-id NamedParam (candidates for set_type_eid) with the parameter id, target element and its class. The param id differs between Revit years even for the same symbol, so scan the file you will edit. usage: tools/rvt_scan_type_eid.py FILE.rvt   (Autodesk samples only; read-only; first 5 hits)"""
import sys,os,glob
sys.path[:0]=['~/src/rvt-ballet',os.path.expanduser('~/rvt-research'),os.path.expanduser('~/rvt-research/write-lab'),os.path.expanduser('~/rvt-research/edit-lab')]
os.environ.update(RVT_GEOM='1')
import wledit, rvt_params
from rvtballet import edit
if len(sys.argv) != 2: sys.exit(__doc__)
f=sys.argv[1]
b=rvt_params.params(f); g=lambda x:x.get('params',x) if isinstance(x,dict) else {}
import rvtgen
class _E: pass
ed=_E(); ed.g=rvtgen.Gen(f); found=0
for e in list(b):
    if 'Family Name' not in g(b[e]) or 'Type Name' not in g(b[e]): continue
    try: tr=ed.g.e.trace(e)
    except Exception: continue
    if tr[2].get('class')!='FamilySymbol': continue
    for l in tr[3]:
        if l[1]=='NamedParam.m_elemId':
            v=edit._eid_val(l[4])
            if v and v>0:
                try: cl=ed.g.e.trace(v)[2].get('class')
                except Exception: continue
                pid=[edit._eid_val(x[4]) for x in tr[3] if x[1]=='NamedParam.m_paramId' and abs(x[2]-l[2])<200]
                print('sym',e,'pid',pid[:3],'-> elem',v,cl); found+=1; break
    if found>=5: break
print('done',found)
