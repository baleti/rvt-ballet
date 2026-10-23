"""vc_scene3d.py FILE.rvt: which prim / element classes the sheets scene (rvtsheets.drawings.scene_text, default options) of every 3D view holds. Run on host1 (h1run, env rvt)."""
import sys, os, time, json
from collections import Counter
sys.path.insert(0, os.path.expanduser(os.environ.get('RVTSHEETS', '~/src/rvt-sheets')))
from rvtsheets.drawings import Model, scene_text
m = Model(os.path.abspath(sys.argv[1])); m.start()
while m.state in ('idle', 'loading'): time.sleep(0.5)
m.decoder()
for v in m._summary['views']:
    if v['kind'] != '3d': continue
    t0 = time.time()
    try:
        d = json.loads(scene_text(m, v['id'], {}))
        c = Counter((d['elements'].get(str(p.get('elem'))) or {}).get('cls', '?') for p in d['prims'])
        print(v['id'], v['name'], 'prims', len(d['prims']), dict(c.most_common(8)), '%.1fs' % (time.time() - t0), flush=True)
    except Exception as ex: print(v['id'], v['name'], 'ERR', str(ex)[:120], flush=True)
