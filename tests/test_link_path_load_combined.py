"""c1x-rvtlink item 95b/95c: (1) via edit.apply, [set_link_path, set_link_load False] on one link type both land and [path Q3, path Q4] reads back Q4 with the load flag still 1 (coalesced);
(2) the internal _apply_rvtedit refuses two un-coalesced path ops on one eid (without the guard the second one flipped m_shouldLoadSource 1 -> 0)."""
import os, sys, tempfile
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SEED = os.path.expanduser('~/c5x-link/al/seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LINKPATH'] = '1'; os.environ['RVTBALLET_ENABLE_LINKLOAD'] = '1'
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
import rvtedit
from rvtballet import edit
def rb(f):
    log = rvtedit.Edit(f).g.e.trace(1363937)[3]
    return {l[1]: str(l[4]) for l in log if l[1] in ('ModelPath.m_path', 'RvtLinkSymbol.m_shouldLoadSource')}
d = tempfile.mkdtemp(); buf = open(SEED, 'rb').read()
def run(ops):
    o = os.path.join(d, 'o%d.rvt' % len(os.listdir(d))); open(o, 'wb').write(edit.apply(buf, ops)); return rb(o)
P = lambda v: {'op': 'set_link_path', 'eid': 1363937, 'value': v}
r = run([P('C:\\z\\Q2.rvt'), {'op': 'set_link_load', 'eid': 1363937, 'value': False}])
assert r == {'ModelPath.m_path': 'C:\\z\\Q2.rvt', 'RvtLinkSymbol.m_shouldLoadSource': '0'}, r
r = run([P('C:\\z\\Q3.rvt'), P('C:\\z\\Q4.rvt')])
assert r == {'ModelPath.m_path': 'C:\\z\\Q4.rvt', 'RvtLinkSymbol.m_shouldLoadSource': '1'}, r
try: edit._apply_rvtedit(SEED, os.path.join(d, 'x.rvt'), [P('C:\\z\\Q3.rvt'), P('C:\\z\\Q4.rvt')])
except edit.EditError as e: assert 'un-coalesced' in str(e), e
else: raise SystemExit('internal route accepted two path ops on one eid')
print('OK combined ops, coalesced and internal guard')
