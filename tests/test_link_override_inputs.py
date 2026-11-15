"""c5x-rvtlink: set_link_override with bad ids (missing, None, negative, bool, str) must raise EditError before any change. Autodesk 2024 HVAC seed (local ~/c5x-link/al/seed.rvt, skipped if absent)."""
import os, sys
SEED = os.path.expanduser('~/c5x-link/al/seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import rvtedit
from rvtballet import edit
ed = rvtedit.Edit(SEED)
for o in ({'eid': 1363877, 'link': 1363877, 'linked_view': 1363877}, {'eid': 1363877, 'link': 124186, 'linked_view': 1363937}, {'eid': 99999999, 'link': 1363937, 'linked_view': 1}, {'eid': 1363938, 'link': None, 'linked_view': None}, {'eid': 1363938, 'link': -1, 'linked_view': 1}, {'eid': True, 'link': 1363937, 'linked_view': 1}, {'eid': 1363938, 'link': 1363937, 'linked_view': 'a'}):
    try: edit._set_link_override(ed, o); raise SystemExit('accepted %r' % (o,))
    except edit.EditError: pass
print('OK link override input guards')
