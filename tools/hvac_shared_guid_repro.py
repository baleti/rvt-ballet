"""repro (c4x-rvtmatrix): set_string IfcGUID on duct 1379374 of the public 2024 Snowdon HVAC sample also changes IfcGUID/Type IfcGUID of 1379375 (shared string storage); the gate refuses the save (verify_failed el:1379375). Needs ~/rvtfix/corpus/2024/42_*HVAC.rvt."""
import os,sys
sys.path[:0]=['~/src/rvt-viewer',os.path.expanduser('~/rvt-research'),os.path.expanduser('~/rvt-research/write-lab')]
os.environ['RVTBALLET_EDIT_BACKEND']='rvtedit'
from rvtballet import edit
import rvt_params
F=os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt'); b=open(F,'rb').read()
p=rvt_params.params(F)
for e in (1379374,1379375): print(e, {k:v for k,v in list((p.get(e) or {}).get('params',p.get(e) or {}).items())[:12]})
q=p[1379374]; q=q.get('params',q)
print([k for k,v in q.items() if isinstance(v,str)])
for eid in (1379374,):
  qq=p[eid]; qq=qq.get('params',qq)
  for nm in ('IfcGUID',):
    if nm in qq and isinstance(qq[nm],str):
        o=edit.validate_op({'op':'set_string','eid':eid,'param':nm,'value':'zzTEST'}); nb,_=edit.apply_full(b,[o])
        open('/tmp/dd_out.rvt','wb').write(nb); p2=rvt_params.params('/tmp/dd_out.rvt')
        for e in (1379374,1379375):
            a=p[e].get('params',p[e]); c=p2[e].get('params',p2[e]); print(eid,nm,e,{k:(a.get(k),c.get(k)) for k in set(a)|set(c) if a.get(k)!=c.get(k)})
