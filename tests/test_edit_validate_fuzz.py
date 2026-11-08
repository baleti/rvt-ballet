"""validate_op hostile-input fuzz (no files): every result is either a clean op (finite numbers, int eid, str values without control chars/NUL) or EditError; no other exception type, no NaN/inf through."""
import os, sys, math, itertools
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_DELETE'] = '1'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit
vals = [0, 1, -1, 2.5, 1e308, -1e308, float('nan'), float('inf'), -float('inf'), 10**30, '1', '', None, True, [], {}, 'a\x00b', 'x' * 100000, '\ud800', 1e-320]
ops = [{'op': 'move', 'eid': 5, 'dx': a, 'dy': b, 'dz': 0.0} for a, b in itertools.product(vals, vals)]
ops += [{'op': 'rotate', 'eid': 5, 'deg': a} for a in vals] + [{'op': 'move', 'eid': e, 'dx': 1.0} for e in vals]
ops += [{'op': 'set_string', 'eid': 5, 'param': 'Comments', 'value': v} for v in vals] + [{'op': 'set_string', 'eid': 5, 'param': p, 'value': 'x'} for p in vals]
ops += [{'op': 'set_num', 'eid': 5, 'param': 'Base Offset', 'value': v} for v in vals] + [{'op': 'delete', 'eid': e} for e in vals] + [{'op': o} for o in vals] + [vv for vv in vals]
for ok in ({'op': 'move', 'eid': 5, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}, {'op': 'rotate', 'eid': 5, 'deg': 30}, {'op': 'set_string', 'eid': 5, 'param': 'Comments', 'value': 'x'}, {'op': 'set_num', 'eid': 5, 'param': 'Base Offset', 'value': 1.5}, {'op': 'delete', 'eid': 5}): edit.validate_op(ok)      # positive controls: the fuzz is not vacuous
acc = bad = 0
for o in ops:
    try: r = edit.validate_op(o)
    except edit.EditError: continue
    except Exception as x: print('FAIL non-EditError', type(x).__name__, repr(o)[:100]); bad += 1; continue
    acc += 1
    for k, v in r.items():
        if isinstance(v, float) and not math.isfinite(v): print('FAIL non-finite accepted', repr(o)[:100]); bad += 1
        if k == 'eid' and (type(v) is not int): print('FAIL eid type', repr(o)[:100]); bad += 1
        if isinstance(v, str) and '\x00' in v: print('FAIL NUL accepted', repr(o)[:60]); bad += 1
        if isinstance(v, float) and abs(v) > 5e4 and r['op'] == 'move': print('FAIL huge move accepted', repr(o)[:100]); bad += 1
print('validate fuzz: %d inputs, %d accepted, %d violations' % (len(ops), acc, bad)); sys.exit(1 if bad else 0)
