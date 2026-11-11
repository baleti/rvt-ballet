"""Stored-int 'Bool' params that the real Revit ignores (VM readback: Return Airflow, Power Load Units, Lighting Load Units on the Autodesk Snowdon HVAC sample, 2024 and 2025) are refused at validate_op instead of being saved as an edit that does nothing."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit
for name in ('Return Airflow', 'Power Load Units', 'Lighting Load Units'):
    try: edit.validate_op({'op': 'set_num', 'eid': 1410856, 'param': name, 'value': 1, 'kind': 'Int'})
    except edit.EditError as e: assert 'real Revit' in str(e) and 'nothing was changed' in str(e), e
    else: raise SystemExit('FAIL: %s accepted' % name)
print('ignored-int params refused')
