"""a move is only accepted for classes with a Revit-verified implementation (edit.MOVE_VM_VERIFIED); a class outside the list is refused with a clear EditError, the opt-out RVTBALLET_MOVE_ANY=1 restores the old behaviour.
Autodesk-style synthetic scene cols2 (FamilyInstance 301595); skipped when absent."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
F = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import edit
if not os.path.exists(F): print('skip'); sys.exit(0)
buf = open(F, 'rb').read(); op = edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0})
edit.apply_full(buf, [op]); print('FamilyInstance accepted (in list)')
keep = edit.MOVE_VM_VERIFIED; edit.MOVE_VM_VERIFIED = frozenset()
try:
    try: edit.apply_full(buf, [op]); print('FAIL accepted outside the list'); sys.exit(1)
    except edit.EditError as e: assert 'no Revit-verified' in str(e), e; print('refused outside the list')
finally: edit.MOVE_VM_VERIFIED = keep
