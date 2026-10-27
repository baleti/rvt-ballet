"""time the Rust mesh stream (model.start_meshes) on a file, chunk by chunk, to see where it stalls: tools/stream_stall.py FILE.rvt [CHUNK=128]; use a fresh RVT_CORE_CACHE for a cold run"""
import sys, os, time
sys.path.insert(0, os.path.expanduser('~/src/rvt-core/python')); import rvt_fast as RF
m = RF.Model(sys.argv[1]); ids = list(m.mesh_ids()); ch = int(sys.argv[2]) if len(sys.argv) > 2 else 128
print('ids', len(ids), flush=True); t0 = time.time(); n = 0; last = t0
for part in m.start_meshes(ids, chunk=ch):
    n += len(part); now = time.time()
    if now - last > 5: print('GAP %.1fs before %d/%d (t=%.0f) ids=%s' % (now - last, n, len(ids), now - t0, [int(e) for e, _ in part][:3]), flush=True)
    last = now
print('DONE %.0fs' % (time.time() - t0), flush=True)
