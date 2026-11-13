"""c3x-rvtdiff: set_type_eid on a derived symbol (2024 HVAC 1530089, master 1379030) is refused."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_TYPEPARAM'] = '1'; os.environ['RVTBALLET_ENABLE_TYPEEID'] = '1'
d = os.path.expanduser('~/rvt-research/corpus/2024')
F = [os.path.join(d, n) for n in os.listdir(d) if n.endswith('HVAC.rvt')] if os.path.isdir(d) else []
from rvtballet import edit, save
if not F or not save._import(): print('skip'); sys.exit(0)
buf = open(F[0], 'rb').read()
try:
    edit.apply_full(buf, [edit.validate_op({'op': 'set_type_eid', 'eid': 1530089, 'pid': 579119, 'target': 579118})])
except edit.EditError as x:
    assert 'derived symbol' in str(x), str(x); print('ok: refused:', str(x)[:90]); sys.exit(0)
raise SystemExit('FAIL: derived symbol edit accepted')
