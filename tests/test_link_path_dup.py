"""c5x-rvtlink: set_link_path must refuse a path that another link type already has (Revit 2024 VM 2026-11-13: two link types on one file both fail to load).
Autodesk Snowdon HVAC 2024 sample (local ~/c5x-link/al/seed.rvt, skipped if absent): Architectural link path (any case/slash) refused; a new path and the own path accepted."""
import os, sys
SEED = os.path.expanduser('~/c5x-link/al/seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LINKPATH'] = '1'
import rvtedit
from rvtballet import edit
ed = rvtedit.Edit(SEED)
for v in ('Snowdon Towers Sample Architectural.rvt', 'SNOWDON TOWERS SAMPLE ARCHITECTURAL.RVT'):
    try: edit._set_link_path(ed, {'eid': 1363937, 'value': v}); raise SystemExit('duplicate path accepted: ' + v)
    except edit.EditError as e: assert 'one link type per file' in str(e), e
for v in ('Brand_New.rvt', 'Brand_Newer.rvt'): edit._set_link_path(ed, {'eid': 1363937, 'value': v})
for v in ('a<b>.rvt', 'a|b?c*.rvt', '..\\x\\..\\y.rvt', 'COM1.rvt', 'trail.rvt .', '', 'a\ud800b.rvt', 'd\\' * 130 + 'x.rvt'):
    try: edit._set_link_path(ed, {'eid': 1363937, 'value': v}); raise SystemExit('odd path accepted: %r' % v)
    except edit.EditError: pass
for e in (99999999, -1):
    try: edit._set_link_path(ed, {'eid': e, 'value': 'x.rvt'}); raise SystemExit('missing eid accepted')
    except edit.EditError: pass
print('OK link path duplicate guard')
