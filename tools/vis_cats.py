# host1 diagnostic: which categories the sheets visibility engine hides in a Snowdon Structural plan, and what element classes it keeps (view 581543); run with rvt-env python
import sys; sys.path.insert(0,'/home/user1/src/rvt-ballet')
from rvtballet.vscene_worker import Worker
w=Worker('/home/user1/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
vis=w.d.vis; v0=vis.doc['views'].get(581543) or vis.doc['views'].get('581543'); v=vis.effective(v0)
hid,x=vis.hidden_categories(v)
cats=vis.doc['categories']
print(sorted((c,cats.get(c,{}).get('name')) for c in hid)[:60])
out,why=vis.elements(581543,explain=True)
import collections
c=collections.Counter(); 
for e,s in out.items():
    i=vis.info.info.get(e) or {}; c[(i.get('cls'),cats.get(i.get('cat'),{}).get('name'))]+=1
print(c.most_common(25))
