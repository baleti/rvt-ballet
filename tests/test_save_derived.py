"""derived_echoes (QUEUE 64): strict rule on reader dicts: an UNEDITED element that changed in exactly the edited parameter, from the edited element's old value to its new value, is a derived echo; anything else (other
parameter changed too, different old/new value, no change) is not."""
import os, sys
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
from rvtballet import save
A = {1: {'Detail Level': 3, 'Mark': 'a'}, 2: {'Detail Level': 3, 'Mark': 'b'}, 3: {'Detail Level': 3, 'Mark': 'c'}, 4: {'Detail Level': 2}, 5: {'Detail Level': 3}, 6: {'x': 1}}
B = {1: {'Detail Level': 1, 'Mark': 'a'}, 2: {'Detail Level': 1, 'Mark': 'b'}, 3: {'Detail Level': 1, 'Mark': 'CHANGED'}, 4: {'Detail Level': 1}, 5: {'Detail Level': 3}, 6: {'x': 1}}
mem = {}
save._read_params = lambda buf: mem[buf]
mem[b'a'] = A; mem[b'b'] = B
op = {'op': 'set_num', 'eid': 1, 'param': 'Detail Level', 'value': 1, 'kind': 'Int'}
got = save.derived_echoes(b'a', b'b', [op])
assert got == [2], got      # 2 = echo; 3 also changed Mark (not an echo, stays undeclared); 4 had another old value; 5 unchanged
assert save.derived_echoes(b'a', b'b', [{'op': 'move', 'eid': 1, 'dx': 1.0}]) == []
assert save.derived_echoes(b'a', b'b', [dict(op, param='Mark')]) == []
print('derived echoes OK:', got)
mem[b'c'] = {1: {'Name': 'V1'}, 2: {'View Name': 'V1', 'x': 1}, 3: {'View Name': 'V1', 'x': 1}, 4: {'View Name': 'Other'}}
mem[b'd'] = {1: {'Name': 'V2'}, 2: {'View Name': 'V2', 'x': 1}, 3: {'View Name': 'V2', 'x': 2}, 4: {'View Name': 'Other'}}
assert save.derived_echoes(b'c', b'd', [{'op': 'set_string', 'eid': 1, 'param': 'Name', 'value': 'V2'}]) == [2]   # 3 also changed x: not an echo
mem[b'e'] = {1: {'View Name': 'V1'}, 2: {'View Name': 'V1', 'Sheet Name': 'V1'}, 3: {'View Name': 'V1', 'Sheet Name': 'V1', 'Mark': 'm'}, 4: {'Comments': 'V1'}, 5: {'View Name': 'V1', 'Sheet Name': 'keep'}}
mem[b'f'] = {1: {'View Name': 'V2'}, 2: {'View Name': 'V2', 'Sheet Name': 'V2'}, 3: {'View Name': 'V2', 'Sheet Name': 'V2', 'Mark': 'n'}, 4: {'Comments': 'V2'}, 5: {'View Name': 'V2', 'Sheet Name': 'keep'}}
rn = {'op': 'set_string', 'eid': 1, 'field': 'DBView.m_viewName', 'value': 'V2', 'match': 'V1'}
assert save.derived_echoes(b'e', b'f', [rn]) == [2, 5]   # 3 also changed Mark; 4 not a view-name key
print('view rename echo OK')
# column location mark after a move (read-back tolerance, QUEUE 73o): only the trailing offset may change
f = save._same_mark_base
assert f('D-1', 'D-1(610)') and f('W(137)-16(1162)', 'W(137)-16(1467)') and f('W(137)-16', 'W(137)-16')
assert not f('W(137)-16(1162)', 'W(137)-17(1467)') and not f('A', 'B(5)') and not f('A(5)', 'B')
assert f('D-1(610)', 'D-1') and not f('', 'anything') and not f('', '')      # moved back onto the grid line; an empty old mark never matches
print('mark base OK')
# compose(): repeated ops of one element merged (QUEUE 83)
from rvtballet.edit import compose
mv = lambda e, d: {'op': 'move', 'eid': e, 'dx': d, 'dy': 0.0, 'dz': 0.0}
ss_ = lambda e, v: {'op': 'set_string', 'eid': e, 'param': 'Comments', 'value': v, 'kind': 'AString', 'pid': None}
assert compose([mv(1, 2.0), mv(1, -2.0)]) == [] and compose([mv(1, 2.0), mv(1, 1.0)])[0]['dx'] == 3.0
assert [o['value'] for o in compose([ss_(2, 'a'), ss_(2, 'b')])] == ['b']
assert compose([{'op': 'rotate', 'eid': 4, 'deg': 180.0}, {'op': 'rotate', 'eid': 4, 'deg': 180.0}]) == []
assert compose([mv(3, 1.0), {'op': 'delete', 'eid': 3}, {'op': 'delete', 'eid': 3}]) == [{'op': 'delete', 'eid': 3}]
assert len(compose([ss_(2, 'a'), ss_(5, 'a')])) == 2
print('compose OK')
