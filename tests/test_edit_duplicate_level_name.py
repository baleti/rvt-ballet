"""c5x-rvtread: renaming a Level onto a sibling Level's name (exact or case variant) is refused; a fresh name passes. Autodesk 2024 Construction template (skips when absent)."""
import os, sys
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(SRC): print('skip: no template'); sys.exit(0)
sys.path.insert(0, os.path.expanduser('~/rvt-research'))
from rvtballet import edit
def tryname(v):
    try: edit._check_datum_name_unique(SRC, {'eid': 5877, 'value': v, 'field': 'DatumPlane.m_text'}); return 'ok'
    except edit.EditError as e: return 'refused'
assert tryname('T.O. Fnd. Wall') == 'refused'
assert tryname('t.o. fnd. wall') == 'refused'
assert tryname(' T.O. FND. WALL ') == 'refused'
assert tryname('T.O. Slab') == 'ok'          # unchanged name (own element) is fine
assert tryname('T.O. Slab c5x') == 'ok'
assert tryname('Level 1') == 'refused'
def tryview(eid, v):
    try: edit._check_datum_name_unique(SRC, {'eid': eid, 'value': v, 'field': 'DBView.m_viewName'}); return 'ok'
    except edit.EditError: return 'refused'
assert tryview(356, 'Level 1 c5x') == 'ok'
import rvt_entities
vs = {k: v['fields'].get('m_viewName') for k, v in rvt_entities.extract(SRC, slim=lambda c: c == 'DBViewSection')['recs'].items() if k[1] == 'DBViewSection'}
(a, na), (b, nb) = list(vs.items())[:2]
assert tryview(a[0], nb.upper()) == 'refused' and tryview(a[0], na + ' c5x') == 'ok'
for v in ('', '  ', 'a:b', 'a|b', 'x{y}', 'a\\b', 'a<b>', 'q?', 'a;b', 'a`b', 'a~b', 'a[1]', 'a\nb', 'a\tb', 'a\x7fb', 'N' * 256):
    try: edit._check_element_name(v); raise SystemExit('accepted %r' % v)
    except edit.EditError: pass
edit._check_element_name('N' * 255)
edit._check_element_name('Level 1 - ok (a) #2 &')
print('ok duplicate level names refused')
