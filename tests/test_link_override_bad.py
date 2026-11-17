"""c9x-rvtlink: set_link_override must refuse bad targets (never write a dangling reference). Local HVAC 2024 sample file ov_A; skips if absent."""
import os, sys
A = os.path.expanduser('~/c9x-rvtlink-work/ovrp2024/ov_A.rvt')
if not os.path.exists(A): print('SKIP'); sys.exit(0)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.expanduser('~/src/rvt-extract')); sys.path.insert(0, os.path.expanduser('~/rvt-research'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LINKOVERRIDE'] = '1'
from rvtballet import edit
ab = open(A, 'rb').read()
good = {'op': 'set_link_override', 'eid': 1363877, 'link': 1363937, 'linked_view': 124186}
cases = {'link is an instance not a type': dict(good, link=1363938), 'link nonexistent': dict(good, link=999999999), 'view nonexistent': dict(good, eid=999999999),
         'eid not a view (a link symbol)': dict(good, eid=1363937), 'linked_view 0': dict(good, linked_view=0), 'linked_view negative': dict(good, linked_view=-5), 'linked_view huge': dict(good, linked_view=2**70), 'linked_view string': dict(good, linked_view='x'), 'link bool': dict(good, link=True)}
bad = []
for k, op in cases.items():
    try: nb, _ = edit.apply_full(ab, [op]); bad.append((k, 'ACCEPTED, output differs' if nb != ab else 'accepted noop'))
    except edit.EditError as e: print('refused:', k, '|', str(e)[:80])
    except Exception as e: bad.append((k, 'CRASH ' + type(e).__name__ + ' ' + str(e)[:80]))
print('FAIL' if bad else 'PASS', bad)
sys.exit(1 if bad else 0)
