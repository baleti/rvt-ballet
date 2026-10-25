"""find elements whose Rust saved-graphics mesh decode is slow (the corpus-008 stall): usage tools/find_slow_mesh.py FILE.rvt [SLOW_SECS=3] -> prints one line per element slower than SLOW_SECS, and the id being decoded is kept in /tmp/find_slow_mesh.cur (so a hang names its element)"""
import sys, os, time
sys.path.insert(0, os.path.expanduser('~/src/rvt-core/python')); import rvt_fast as RF
path = sys.argv[1]; slow = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
m = RF.Model(path); ids = list(m.mesh_ids()); md = RF.mesh_doc(m.doc()); print('elements with meshes: %d' % len(ids), flush=True)
t0 = time.time()
for k, e in enumerate(ids):
    open('/tmp/find_slow_mesh.cur', 'w').write('%d %d\n' % (k, e))
    t = time.time()
    try: r = md.element_meshes([int(e)], compact=True)[0]
    except Exception as ex: r = None; print('err', e, repr(ex), flush=True)
    dt = time.time() - t
    if dt > slow: print('SLOW id=%d index=%d %.1fs tris=%s' % (e, k, dt, None if r is None else len(r['tris'])), flush=True)
    if k % 500 == 0: print('progress %d/%d %.0fs' % (k, len(ids), time.time() - t0), flush=True)
print('DONE %.0fs' % (time.time() - t0), flush=True)
