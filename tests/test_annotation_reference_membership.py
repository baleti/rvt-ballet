"""c1x-rvtmove 2026-11-16: an element named by SpotElevation / Rebar / Alignment records (m_elemId) is flagged 'referenced by N annotation/rebar element(s)' so an in-place move or rotate is refused (Snowdon Structural 2024: 630 SpotElevations name FamilyInstances, e.g. 606873; Revit recomputes them, the writer moves the instance only). Autodesk sample, local corpus; skipped without it."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
F = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
if not os.path.exists(F): print('skip'); sys.exit(0)
from rvtballet import save
m = save.membership(open(F, 'rb').read(), [606873, 606893])
assert any(x.startswith('referenced by') for x in m.get(606873, [])), m
assert any(x.startswith('referenced by') for x in m.get(606893, [])), m      # 11 Rebar records name 606893
assert 606873 in save.risky_membership(m, [{'op': 'move', 'eid': 606873}])
print('annotation/rebar reference membership OK')
