"""regression (c3x-rvtmatrix, severity 1): a value with a non-BMP character (emoji) saved with rvtedit by-name edits and was ACCEPTED by the gate, but the element's parameters then read back truncated
(13 of 26, edited one None). validate_op must refuse such values for every string path; BMP text (accents, CJK, RTL, combining) stays allowed."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import edit
for op in ({'op': 'set_string', 'eid': 5, 'value': 'x \U0001F600', 'param': 'Comments'}, {'op': 'set_string', 'eid': 5, 'value': '\U00020000', 'field': 'DatumPlane.m_text'}, {'op': 'set_string', 'eid': 5, 'value': 'a\U0001F600', 'match': ''}):
    try: edit.validate_op(op); raise SystemExit('FAIL accepted %r' % op['value'])
    except edit.EditError as e: assert 'Basic Multilingual' in str(e)
for v in ('Ünïcödé', '日本語', 'שלום', 'é', 'x' * 4096): edit.validate_op({'op': 'set_string', 'eid': 5, 'value': v, 'param': 'Comments'})
print('edit text OK')
