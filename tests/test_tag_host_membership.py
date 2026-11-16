"""c1x-rvtmove 2026-11-16: an instance named as host by an IndependentTag (m_linkInstOrHostId) is flagged 'referenced by N annotation/rebar element(s)' so an in-place move is refused (Electrical 2024: 6 such instances were unflagged before)."""
import os, sys, re
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), os.path.expanduser('~/rvt-research')]
F = os.path.expanduser('~/rvt-research/corpus/2024/44_Snowdon_Towers_Sample_Electrical.rvt')
if not os.path.exists(F): print('skip'); sys.exit(0)
import rvt_xcache
from rvtballet import save
x = rvt_xcache.get_x_ro(F)
cls = {e: c for (e, c) in x['recs']}; host = None
for (e, c), r in x['recs'].items():
    if c == 'IndependentTag':
        for mm in re.finditer(r"m_linkInstOrHostId': EID\((\d+)\)", str(r.get('fields'))):
            h = int(mm.group(1))
            if h < 2 ** 32 - 1 and cls.get(h) == 'FamilyInstance': host = h; break
    if host: break
assert host, 'no tagged FamilyInstance found'
m = save.membership(open(F, 'rb').read(), [host])
assert any(s.startswith('referenced by') for s in m.get(host, [])), (host, m)
assert host in save.risky_membership(m, [{'op': 'move', 'eid': host}])
print('tag host membership OK', host)
