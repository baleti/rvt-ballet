"""Int set_num on a material's Class / Behavior is refused at validate_op (the reader shows the asset value, so the save-time read-back would refuse it later with 422: found on the Autodesk 2024 HVAC sample, element 18435)."""
import os, sys
os.environ.setdefault('RVTBALLET_EDIT_BACKEND', 'rvtedit')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit
for p in ('Class', 'Behavior'):
    try: edit.validate_op({'op': 'set_num', 'eid': 18435, 'param': p, 'value': 1, 'kind': 'Int'})
    except edit.EditError as e: assert 'cannot be verified' in str(e), e
    else: raise SystemExit('FAIL: %s accepted' % p)
print('material Class/Behavior refused early')
