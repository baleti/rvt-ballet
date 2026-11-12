"""Int set_num on Discipline with a value that is not one of the bit-flag choices (3, 5, 6, 0, -1) is refused at validate_op (Revit 2024 and 2026 VM readback: blank choice name); the real values 1, 2, 4, 8, 16, 4095 pass this check."""
import os, sys
os.environ.setdefault('RVTBALLET_EDIT_BACKEND', 'rvtedit')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit
for v in (3, 5, 6, 0, -1):
    try: edit.validate_op({'op': 'set_num', 'eid': 160625, 'param': 'Discipline', 'value': v, 'kind': 'Int'})
    except edit.EditError as e: assert 'not a valid choice' in str(e), e
    else: raise SystemExit('FAIL: Discipline %d accepted' % v)
for v in (1, 2, 4, 8, 16, 4095):
    try: edit.validate_op({'op': 'set_num', 'eid': 160625, 'param': 'Discipline', 'value': v, 'kind': 'Int'})
    except edit.EditError as e: assert 'not a valid choice' not in str(e), e
    except Exception: pass      # later checks (parameter lookup) are not the subject here
print('Discipline enum check ok')
