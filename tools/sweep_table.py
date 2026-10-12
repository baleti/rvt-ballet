"""~/.cache/rvt-viewer/sweep.jsonl -> docs/SWEEP.md (per file: status, size, seconds, elements, fidelity, sheets/views, failure reason)"""
import json, os, collections
R = [json.loads(l) for l in open(os.path.expanduser('~/.cache/rvt-viewer/sweep.jsonl'))]
last = collections.OrderedDict()
for r in R: last[r['src']] = r
R = sorted(last.values(), key=lambda r: (r['year'], r['file']))
def func(r):
    f = r.get('func')
    if not f: return '-'
    bad = [k for k, c in (f.get('checks') or {}).items() if not c.get('ok')]
    return 'PASS' if f.get('ok') else 'FAIL: ' + ', '.join(bad or [f.get('error', '?')])
pc = lambda x: '' if x is None else '%d%%' % round(100 * x)
L = ['# Corpus sweep: every corpus file converted as `rvt-view` does (tools/sweep.py)', '',
     'ok %d / %d files; failures listed with their reason. Columns: true geometry / parametric matched / approximate / box only (building elements).' % (sum(r['status'] == 'ok' for r in R), len(R)), '',
     '| year | file | MB | convert | s | elements | tris | true | matched | approx | box | sheets/views | materials used (swatches) | functional checks |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
for r in R:
    L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (r['year'], r['file'], r['mb'], r['status'], r['secs'], r.get('elements', ''), r.get('tris', ''), pc(r.get('true')), pc(r.get('matched')), pc(r.get('approx')), pc(r.get('box')),
             '%s/%s' % (r.get('sheets', ''), r.get('views', '')), '%s (%s)' % (r.get('mat_used', ''), r.get('swatches', '')), func(r)))
bad = [r for r in R if r['status'] != 'ok' or (r.get('func') and not r['func'].get('ok'))]
if bad:
    L += ['', '## Failures', '']
    for r in bad:
        L.append('* %s/%s: %s rc=%s: `%s`' % (r['year'], r['file'], r['status'], r.get('rc'), (r.get('err') or '').strip().splitlines()[-1][:300] if r.get('err') else ''))
        for k, c in ((r.get('func') or {}).get('checks') or {}).items():
            if not c.get('ok'): L.append('  * %s: `%s`' % (k, json.dumps(c.get('info'))[:300]))
open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs', 'SWEEP.md'), 'w').write('\n'.join(L) + '\n'); print('\n'.join(L[:6]))
