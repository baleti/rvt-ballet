#!/usr/bin/env python3
"""rvtdel_ehloss.py FILE [N]: delete up to N elements one at a time (opt-in delete, rvtedit backend) and report, per delete, the ElementHeader keys that vanish from the output besides the deleted ids (a surviving element losing its header = the writer cut a neighbour: c5x-rvtread item 82). Exit 1 if any survivor loses a header. Local files only."""
import os, sys, tempfile
os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')] + [os.path.expanduser('~/rvt-research' + s) for s in ('', '/write-lab', '/edit-lab')]
from rvtballet import edit
import rvt_entities as RE, rvt_params
F = os.path.expanduser(sys.argv[1]); N = int(sys.argv[2]) if len(sys.argv) > 2 else 6
buf = open(F, 'rb').read(); a = set(RE.extract(F)['eh']); bad = ok = tried = 0
for e in list(rvt_params.params(F))[:80]:
    if ok >= N or tried >= 4 * N: break
    tried += 1
    try: nb, gone = edit.apply_full(buf, [edit.validate_op({'op': 'delete', 'eid': e})])
    except Exception: continue
    if nb == buf or not gone: continue
    p = tempfile.mkdtemp() + '/o.rvt'; open(p, 'wb').write(nb)
    lost = sorted(a - set(RE.extract(p)['eh']) - set(gone)); ok += 1
    if lost: bad += 1
    print(os.path.basename(F)[:2], e, 'gone', len(gone), 'cut bytes', len(buf) - len(nb), 'SURVIVOR HEADERS LOST' if lost else 'headers ok', lost[:5], flush=True)
print('done', ok, 'deletes', bad, 'with survivor header loss', flush=True); sys.exit(1 if bad else 0)
