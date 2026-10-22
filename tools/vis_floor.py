# host1 diagnostic: resolved graphics (overrides, cut/proj line, sources) of the Floor and one wall in a Snowdon Structural plan (view 581543); run with rvt-env python
import sys, json; sys.path.insert(0, '/home/user1/src/rvt-sheets')
from rvtsheets.decode import Decoder
from rvtsheets.visibility import Visibility
from rvtsheets.vg.resolve import resolve_view
dec = Decoder('/home/user1/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt'); doc = dec.doc(); vis = Visibility(dec, doc)
rep = resolve_view(dec, doc, 581543, vis=vis, explain=True)
seen = set()
for k, e in rep['elements'].items():
    if e['cls'] in seen or e['cls'] not in ('Floor', 'SWall', 'FamilyInstance'): continue
    seen.add(e['cls']); print(k, json.dumps({x: e.get(x) for x in ('cls', 'cat', 'phase', 'overrides', 'cut', 'proj', 'source')}, default=str)[:1500])
print('template', rep.get('template'))
