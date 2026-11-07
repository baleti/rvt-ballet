"""ESCAPE hunt for ANY edit op: apply OPS (json list) with the real rvt-ballet edit path, take the writer's own manifest (incl. dirty_members), then hand N one-bit flips of the result to the gate; every flip must be refused, the true output accepted.
usage: tools/rvt_edit_flip.py SRC.rvt '[{"op":"move","eid":1366142,"dx":1,"dy":0,"dz":0}]' N SEED   (Autodesk samples only; ENV EDIT_FLIP_SKIPCTL=1 skips the control; aggregate output)"""
import os, sys, tempfile, hashlib, shutil, random, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_SNAPSHOT_CACHE=_T + '/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_CHANGETYPE='1')
import atexit; atexit.register(shutil.rmtree, _T, True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
os.environ.setdefault('RVT_GEOM', '1')
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
from rvtballet import save, edit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
src0, ops, n, seed = sys.argv[1], json.loads(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
src = os.path.join(_T, 'src.rvt'); shutil.copy(src0, src); h0 = sha(src); buf = open(src, 'rb').read()
ops = [edit.validate_op(o) for o in ops]
good, deleted = edit.apply_full(buf, ops); dm = edit.last_dirty_members(); m = edit.Edits(); m.ops = ops; man = m.manifest(deleted)
if dm: man['dirty_members'] = dm
if dm and len(ops) == 1 and ops[0].get('op') in ('move', 'rotate'): man['member_span_max'] = 2048      # mirrors save._pending
ech = save.derived_echoes(buf, good, edit.compose(ops))      # same as save._pending: dependents whose derived readback echoes the edit (e.g. level rename -> 'Level' param of its elements)
if ech: man['modified'] = sorted(set(man['modified']) | {'el:%d' % i for i in ech})
print('manifest modified=%d deleted=%d dirty_members=%s' % (len(man.get('modified', ())), len(man.get('deleted', ())), {k: len(v) for k, v in (dm or {}).items()}), flush=True)
rnd = random.Random(seed); ss = save.SaveSessions(); T = {} if os.environ.get('EDIT_FLIP_SKIPCTL') else {'control_true_output': good}
for k in range(n):
    o = rnd.randrange(len(good)); x = bytearray(good); x[o] ^= 1 << rnd.randrange(8); T['flip_%d' % k] = bytes(x)
if os.environ.get('EDIT_FLIP_INMEMBER'):      # targeted: flip one byte of the DECOMPRESSED raw of each declared member, far from the edit (re-encoded through the writer's own partition rebuild), N per member
    import cfb, rvtw, wlpart
    for pn, mem in (dm or {}).items():
        for mi in mem[:int(os.environ.get('EDIT_FLIP_INMEMBER'))]:
            c = cfb.CFB(good); st_ = rvtw.Stream(c.streams()[pn].data); pt = wlpart.Partition(st_)
            r = pt.mem[mi]['raw']; o = rnd.randrange(len(r)); r[o] ^= 1 << rnd.randrange(8); pt.mem[mi]['dirty'] = True
            c.streams()[pn].data = st_.build(pt.rebuild(), keep_spare=False)
            import io; tp = os.path.join(_T, 'rb.rvt'); cfb.write(c, tp); T['inmember_%s_%d_at%d' % (pn.split('/')[-1], mi, o)] = open(tp, 'rb').read()
if os.environ.get('EDIT_FLIP_GLOBAL'):      # targeted: one byte flip in the stream data of every NON-partition stream the writer left unchanged (the gate tolerates Global/* when an edit is declared)
    import cfb
    sa_ = cfb.CFB(buf).streams()
    for sn in sorted(sa_):
        if sn.startswith('Partitions/'): continue
        c = cfb.CFB(good); d = bytearray(c.streams()[sn].data)
        if d != bytearray(sa_[sn].data) or not d: continue
        o = rnd.randrange(len(d)); d[o] ^= 1 << rnd.randrange(8); c.streams()[sn].data = bytes(d)
        tp = os.path.join(_T, 'gl.rvt'); cfb.write(c, tp); T['stream_%s_at%d' % (sn.replace('/', '_'), o)] = open(tp, 'rb').read()
esc = []
for k, nb in T.items():
    dest = os.path.join(_T, 'o_%s.rvt' % k)
    try: save.save_as(ss, 'm', src, dest, new_bytes=nb, manifest=man); acc = True; r = 'ACCEPTED'
    except Exception as e: acc = False; r = type(e).__name__ + ' ' + str(e)[:int(os.environ.get("EDIT_FLIP_MSG", "90"))]
    if acc and k != 'control_true_output': esc.append(k)
    if not acc and k != 'control_true_output': assert not os.path.exists(dest), k
    assert sha(src) == h0
    print(k, r, flush=True)
print('ESCAPES' if esc else 'no escapes', esc, 'n=%d' % n)
