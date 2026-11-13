"""regression (c5x-rvttype 2026-11-13): an edit result containing a partition member above max(131088, largest source member) must be refused (Revit: CorruptModelException on vendor Structural 2024 after a size-growing insert). Synthetic: the member-size probe is patched, no file needed."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit
sizes = {b'src': 131088, b'ok': 131088, b'grown': 262160, b'srcbig': 142000, b'okbig': 142000, b'overbig': 142001}
edit._max_member_raw = lambda b: sizes[b]
bad = 0
for s, o, refuse in ((b'src', b'ok', False), (b'src', b'grown', True), (b'srcbig', b'okbig', False), (b'srcbig', b'overbig', True)):
    try: edit._check_member_limit(s, o); r = False
    except edit.EditError: r = True
    if r != refuse: print('FAIL', s, o, r); bad += 1
print('FAIL' if bad else 'ok'); sys.exit(1 if bad else 0)
