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
