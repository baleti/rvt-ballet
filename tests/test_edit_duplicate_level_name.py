"""c5x-rvtread: renaming a Level onto a sibling Level's name (exact or case variant) is refused; a fresh name passes. Autodesk 2024 Construction template (skips when absent)."""
import os, sys
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(SRC): print('skip: no template'); sys.exit(0)
sys.path.insert(0, os.path.expanduser('~/rvt-research'))
from rvtballet import edit
def tryname(v):
    try: edit._check_datum_name_unique(SRC, {'eid': 5877, 'value': v}); return 'ok'
    except edit.EditError as e: return 'refused'
assert tryname('T.O. Fnd. Wall') == 'refused'
assert tryname('t.o. fnd. wall') == 'refused'
assert tryname(' T.O. FND. WALL ') == 'refused'
assert tryname('T.O. Slab') == 'ok'          # unchanged name (own element) is fine
assert tryname('T.O. Slab c5x') == 'ok'
assert tryname('Level 1') == 'refused'
print('ok duplicate level names refused')
