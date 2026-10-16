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
print('warmed %d scenes; cache dir: .cache/rvt-sheets/%s' % (n, os.path.basename(m.dir)))
