"""tools/vc_classaudit.py: element class counts over the cached view-control scenes (~/.cache/rvt-viewer/vscene), no browser needed."""
import os, json, glob, collections
c = collections.Counter(); n = 0
for p in glob.glob(os.path.expanduser('~/.cache/rvt-viewer/vscene/**/*.json'), recursive=True):
    try: d = json.load(open(p))
    except Exception: continue
    if not isinstance(d, dict) or 'elements' not in d: continue
    n += 1; el = d['elements']
    c.update((e.get('cls') or e.get('class') or '?') for e in (el.values() if isinstance(el, dict) else el) if isinstance(e, dict))
print(n, 'scenes'); [print('%7d %s' % (v, k)) for k, v in c.most_common()]
