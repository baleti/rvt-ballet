"""sweep.jsonl -> results table inside DEMO.md (between the RESULTS markers): per corpus file geometry / materials / views / sheets / functional pass-fail.
usage: tools/demo_table.py [sweep.jsonl]   (pull it from host1 first: h1run pull .cache/rvt-viewer/sweep.jsonl)"""
import json, os, sys, collections, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/.cache/rvt-viewer/sweep.jsonl')
last = collections.OrderedDict()
for l in open(src):
    r = json.loads(l); last[r['src']] = r
R = sorted(last.values(), key=lambda r: (r['year'], r['file']))
def chk(r, k):
    c = ((r.get('func') or {}).get('checks') or {}).get(k)
    return None if c is None else c.get('ok')
def mark(v): return '-' if v is None else ('ok' if v else 'FAIL')
def sheets_cell(r):
    c = ((r.get('func') or {}).get('checks') or {}).get('sheets')
    if not c: return '-'
    i = c.get('info') or {}
    return ('ok %s/%s' % (i.get('sheets'), i.get('views'))) if c.get('ok') else 'FAIL'
L = ['| year | file | MB | convert s | elements | triangles | true geometry | glb | materials used (swatches) | inspector+search | sheets / views drawn | result |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
npass = 0
for r in R:
    f = r.get('func') or {}; ok = r['status'] == 'ok' and f.get('ok'); npass += bool(ok)
    t = r.get('true'); L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s (%s) | %s | %s | **%s** |' % (r['year'], r['file'], r['mb'], r['secs'], r.get('elements', ''), r.get('tris', ''), '' if t is None else '%d%%' % round(100 * t),
        mark(chk(r, 'glb')), r.get('mat_used', ''), r.get('swatches', ''), 'ok' if chk(r, 'inspector') and chk(r, 'search') else mark(chk(r, 'inspector')), sheets_cell(r), 'PASS' if ok else 'FAIL'))
block = ['<!-- RESULTS -->', '', '## Functionality test over the whole corpus (%s, tools/sweep.py + tools/functest.py on host1)' % time.strftime('%Y-%m-%d'), '',
         '**%d / %d files pass** (convert as `rvt-view` does, then through the real server: valid GLB, materials + swatch images, inspector, search, the sheets plug-in with one sheet SVG and one view SVG). "true geometry" = share of building elements drawn from the file\'s own geometry (saved graphics / rebar shapes / decoded B-rep); template (.rte) files have almost no model geometry.' % (npass, len(R)), ''] + L + ['', '<!-- /RESULTS -->']
p = os.path.join(ROOT, 'DEMO.md'); s = open(p).read()
if '<!-- RESULTS -->' in s: s = s[:s.index('<!-- RESULTS -->')] + '\n'.join(block) + s[s.index('<!-- /RESULTS -->') + len('<!-- /RESULTS -->'):]
else: s = s.rstrip('\n') + '\n\n' + '\n'.join(block) + '\n'
open(p, 'w').write(s); print('%d / %d pass' % (npass, len(R)))
