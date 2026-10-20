"""vc_warm_sheets.py FILE.rvt: pre-generate the default view scene (rvt-sheets scene_text, same cache as the sheets server's /view/{id}.json) of every plan / section view.
Run on host1 via tools/vc_warm.sh; then `h1run pull .cache/rvt-sheets/<key dir printed at the end>`."""
import sys, os, time
sys.path.insert(0, os.path.expanduser(os.environ.get('RVTSHEETS', '~/src/rvt-sheets')))
from rvtsheets.drawings import Model, scene_text
m = Model(os.path.abspath(sys.argv[1])); m.start()
while m.state in ('idle', 'loading'): time.sleep(0.5)
m.decoder(); n = 0
for v in m._summary['views']:
    if v['kind'] not in ('plan', 'section'): continue
    t0 = time.time()
    try: scene_text(m, v['id'], {}); n += 1; print('ok', v['id'], v['kind'], v['name'], '%.1fs' % (time.time() - t0), flush=True)
    except Exception as ex: print('FAIL', v['id'], v['name'], repr(ex)[:100], flush=True)
import glob
sc = [f for f in glob.glob(os.path.expanduser('~/.cache/rvt-sheets/*/scene_*.json')) if time.time() - os.path.getmtime(f) < 86400]
d = os.path.basename(os.path.dirname(max(sc, key=os.path.getmtime))) if sc else os.path.basename(m.cache.dir)  # the dir that really holds the newest scenes (m.dir printed a dir that did not exist on host1)
print('warmed %d scenes; cache dir: .cache/rvt-sheets/%s' % (n, d))
