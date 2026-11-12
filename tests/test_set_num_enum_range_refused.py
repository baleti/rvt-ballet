"""Int set_num outside the VM-measured choice range of Detail Level (1..3), Mullion Family General Shape (0..5), Tangent Joins (0..2) is refused at validate_op (Revit 2024 readback: blank name for Detail Level 4, Mullion shape 6, Tangent Joins 3); values inside the range are not refused by this check."""
import os, sys
os.environ.setdefault('RVTBALLET_EDIT_BACKEND', 'rvtedit')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit
def tryit(p, v):
    try: edit.validate_op({'op': 'set_num', 'eid': 9948, 'param': p, 'value': v, 'kind': 'Int'}); return None
    except edit.EditError as e: return str(e)
    except Exception as e: return None      # later checks are not the subject
for p, bad, good in (('Detail Level', (0, 4, -1, 99), (1, 2, 3)), ('Mullion Family General Shape', (6, -1, 50), (0, 3, 5)), ('Tangent Joins', (3, 4, -1), (0, 1, 2))):
    for v in bad: m = tryit(p, v); assert m and 'not a valid choice' in m, (p, v, m)
    for v in good: m = tryit(p, v); assert not (m and 'not a valid choice' in m), (p, v, m)
print('enum ranges ok')
