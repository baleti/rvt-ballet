"""c3x-rvtdiff: change_type to a derived/surrogate FamilySymbol (FamilySymbol.m_masterId set, empty name) must be refused: Revit 2024 API ChangeTypeId rejected 1379181 -> 1530089 on the HVAC sample ('type not valid for this element'). Fails without the m_masterId gate."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_CHANGETYPE'] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit, save
if not F or not save._import(): print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read()
try:
    edit.apply_full(buf, [edit.validate_op({'op': 'change_type', 'eid': 1379181, 'type_eid': 1530089})])
except edit.EditError as x:
    assert 'derived symbol' in str(x), str(x); print('ok: refused:', str(x)[:90]); sys.exit(0)
raise SystemExit('FAIL: derived symbol accepted')
