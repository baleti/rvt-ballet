"""Level elevation move: derived_echoes declares instances whose reader-view 'Elevation from Level' fell by exactly dz (strict), nothing else.
Synthetic reader views (no model needed) + the Autodesk HVAC 2024 sample when present (in-place save accepted, only the Level's bytes differ)."""
import os, sys, hashlib
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path[:0] = [os.path.expanduser('~/src/savegate'), HERE]
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import save
A = {1: {'class': 'Level', 'params': {'Elevation': 8.0}},
     2: {'class': 'FamilyInstance', 'params': {'Elevation from Level': 9.5, 'Coefficient of Utilization': -4e-14, 'Offset From Attachment At Top': -4e-14}},
     3: {'class': 'FamilyInstance', 'params': {'Elevation from Level': 2.0}},
     4: {'class': 'Wall', 'params': {'Mark': 'x'}}}
def mk(kw={}):
    import copy; B = copy.deepcopy(A); B[1]['params']['Elevation'] = 9.0
    B[2]['params'].update({'Elevation from Level': 8.5, 'Coefficient of Utilization': -5e-14, 'Offset From Attachment At Top': -5e-14}); B[3]['params']['Elevation from Level'] = 1.0
    for (e, k), v in kw.items(): B[e]['params'][k] = v
    return B
def run(B, dz=1.0):
    save._RB_MEMO[:] = []; orig = save._read_params
    save._read_params = lambda buf: A if buf == b'a' else B
    try: return save.derived_echoes(b'a', b'b', [{'op': 'move', 'eid': 1, 'dx': 0.0, 'dy': 0.0, 'dz': dz}])
    finally: save._read_params = orig
assert run(mk()) == [2, 3], run(mk())
assert run(mk(), dz=2.0) == [], 'wrong dz must not echo'
assert run(mk({(2, 'Elevation from Level'): 8.4})) == [3], 'wrong delta on one instance must not echo it'
assert run(mk({(2, 'Coefficient of Utilization'): 0.5})) == [3], 'a real change of a noise key must not echo'
B = mk(); B[4]['params']['Mark'] = 'y'; assert run(B) == [2, 3], 'unrelated change is not declared'
B = mk(); B[3]['params']['Comments'] = 'z'; assert run(B) == [2], 'extra changed key blocks the echo'
print('level echo synthetic OK')
