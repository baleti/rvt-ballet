"""exact id->value pairing (rvtedit backend): on DBViewPlan 356 the second Int parameter ('Discipline') changes ONLY Discipline (rvtedit.set_num would edit 'Detail Level', the neighbouring value);
string by name hits the right parameter ('Comments' not 'Manufacturer'). Needs the write-lab scene; skips otherwise."""
import os, sys, tempfile
for p in (os.path.expanduser('~/rvt-research/edit-lab'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research')): sys.path.insert(0, p)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ.setdefault('RVT_GEOM', '1')
SRC = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(SRC): print('skip'); raise SystemExit
from rvtballet import edit; import rvt_params
buf = open(SRC, 'rb').read(); g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
def change(ops, eid):
    nb = edit.apply(buf, [edit.validate_op(o) for o in ops]); p = tempfile.mktemp(suffix='.rte'); open(p, 'wb').write(nb)
    try: a = g(rvt_params.params(SRC).get(eid)); b = g(rvt_params.params(p).get(eid)); return {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)}
    finally: os.remove(p)
assert change([{'op': 'set_num', 'eid': 356, 'param': 'Discipline', 'kind': 'Int', 'value': 2}], 356) == {'Discipline': (1, 2)}
assert change([{'op': 'set_num', 'eid': 356, 'param': 'Detail Level', 'kind': 'Int', 'value': 3}], 356) == {'Detail Level': (1, 3)}
assert change([{'op': 'set_string', 'eid': 24, 'param': 'Comments', 'value': 'c'}], 24) == {'Comments': ('', 'c')}
assert change([{'op': 'set_string', 'eid': 24, 'param': 'Mark', 'value': 'm'}], 24) == {'Mark': ('', 'm')}
print('edit pairing OK: Int (2nd param), Int (1st param), String Comments, String Mark each change exactly the requested parameter')
