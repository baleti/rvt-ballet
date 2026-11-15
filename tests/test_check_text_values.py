"""edit._check_text refuses values the writer cannot encode (NUL, lone surrogate, beyond BMP, >4096) and accepts BMP unicode/long-ish/empty-free text. Synthetic, no files."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from rvtballet import edit

bad = ['a\0b', '\0', 'x' * 4097, '\ud800', 'a\udfffb', '\U0001F600', 'ok\U00020000']
good = ['Zürich-é-日本-Ω', 'x' * 4096, 'a b', 'tab\tq']
for v in bad:
    try: edit._check_text(v)
    except edit.EditError: continue
    raise SystemExit('FAIL: accepted %r' % v[:20])
for v in good:
    try: edit._check_text(v)
    except edit.EditError as e: raise SystemExit('FAIL: refused %r: %s' % (v[:20], e))
print('OK %d refused, %d accepted' % (len(bad), len(good)))
