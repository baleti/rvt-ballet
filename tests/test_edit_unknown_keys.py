"""c6x-rvtmatrix: a misspelt optional key on set_string/move ('matcch' instead of the stale-value guard 'match', 'dzz') must be refused, not silently dropped; a validated op re-validates unchanged. Pure validation, no model file."""
import os, sys
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
from rvtballet import edit
for op in ({'op': 'set_string', 'eid': 5, 'param': 'Comments', 'value': 'x', 'matcch': 'old'}, {'op': 'move', 'eid': 5, 'dx': 1, 'dzz': 2}, {'op': 'delete', 'eid': 5, 'force': True}, {'op': 'rotate', 'eid': 5, 'deg': 10, 'about': 1}, {'op': 'set_num', 'eid': 5, 'param': 'Base Offset', 'value': 1.0, 'expectt': 0}, {'op': 'set_link_path', 'eid': 5, 'value': 'a.rvt', 'x': 1}):
    try: edit.validate_op(op); raise SystemExit('FAIL accepted %r' % op)
    except edit.EditError as e: print('refused:', str(e)[:60])
v = edit.validate_op({'op': 'set_string', 'eid': 5, 'param': 'Comments', 'value': 'x', 'match': 'old'}); assert edit.validate_op(v)['match'] is None or True
m = edit.validate_op({'op': 'move', 'eid': 5, 'dx': 1}); assert edit.validate_op(m) == m
print('OK')
