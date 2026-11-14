"""c3x-rvtdiff audit: move/rotate/delete/set_string on a FamilySymbol (derived 1530089 and master 1379030, 2024 HVAC) are all refused."""
import os, sys
sys.path.insert(0,'~/src/rvt-ballet')
os.environ['RVTBALLET_ENABLE_DELETE']='1'; os.environ['RVTBALLET_EDIT_BACKEND']='rvtedit'; os.environ['RVTBALLET_ENABLE_CHANGETYPE']='1'
d=os.path.expanduser('~/rvt-research/corpus/2024')
F=[os.path.join(d,n) for n in os.listdir(d) if n.endswith('HVAC.rvt')]
from rvtballet import edit
if not F: print('skip'); sys.exit(0)
bad=0
buf=open(F[0],'rb').read()
for op in [{'op':'move','eid':1530089,'dx':1,'dy':0,'dz':0},{'op':'rotate','eid':1530089,'deg':10},{'op':'delete','eid':1530089},{'op':'set_string','eid':1530089,'param':'Comments','value':'x'},{'op':'delete','eid':1379030},{'op':'move','eid':1379030,'dx':1,'dy':0,'dz':0}]:
    try:
        r=edit.apply_full(buf,[edit.validate_op(op)]); print('ACCEPTED',op); bad=1
    except Exception as x: print('refused',op['op'],op['eid'],str(x)[:100])
if bad: raise SystemExit('FAIL: symbol op accepted')
print('ok: all refused')
