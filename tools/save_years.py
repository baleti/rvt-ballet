"""Which Revit years can reach the writer: run saveinfo on every .rvt/.rte given, count by (year, outcome). Aggregate only (no file names).
usage: tools/save_years.py DIR_OR_FILE..."""
import os, sys, re, tempfile, collections, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
files = []
for a in sys.argv[1:]:
    if os.path.isdir(a): files += [os.path.join(r, f) for r, _, fs in os.walk(a) for f in fs if f.lower().endswith(('.rvt', '.rte'))]
    else: files.append(a)
cnt = collections.Counter(); ss = save.SaveSessions()
for i, f in enumerate(files):
    r = ss.info('k%d' % i, f); e = r.get('error', '')
    m = re.search(r'(20[12]\d)', e) or re.search(r'(20[12]\d)', os.path.basename(f))
    y = r.get('version') or (m.group(1) if m else '?')
    cnt[(y, 'OPEN' if r.get('open') else ('REFUSED-version' if 'cannot be saved' in e else 'REFUSED-other: ' + e[:50]))] += 1
    ss.close('k%d' % i)
for k, v in sorted(cnt.items()): print(k[0], k[1], v)
print('files', len(files), 'writer reachable:', sum(v for k, v in cnt.items() if k[1] == 'OPEN'))
