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
if dm and len(ops) == 1 and ops[0].get('op') in ('move', 'rotate', 'set_num'): man['member_span_max'] = 2048      # mirrors save._pending
if dm and len(ops) == 1 and ops[0].get('op') == 'set_string': man['member_span_max'] = 8192 + 2 * len(str(ops[0].get('value', '')))      # moved up (c2x-rvtsave 101e): the digest rule below needs it set
if man.get('member_span_max') and ops[0].get('op') in ('move', 'rotate', 'set_num', 'set_string') and len(ops) == 1: man['member_diff_ranges'] = edit.member_diff_ranges(buf, good, dm)      # mirrors save._pending
if man.get('member_diff_ranges') is not None or dm: man['member_raw_sha256'] = edit.member_raw_digests(good, dm)
ech = save.derived_echoes(buf, good, edit.compose(ops))      # same as save._pending: dependents whose derived readback echoes the edit (e.g. level rename -> 'Level' param of its elements)
if ech: man['modified'] = sorted(set(man['modified']) | {'el:%d' % i for i in ech})
if dm and ops and all(o.get('op') in ('move', 'rotate', 'set_string', 'delete') for o in ops):
    man['frozen_streams'] = True
    if any(o.get('op') == 'delete' for o in ops): man['frozen_except'] = ['Global/ElemTable', 'Global/Latest']
    if len(ops) == 1 and ops[0].get('op') == 'delete': man['member_pure_cut'] = True      # mirrors save._pending
if dm and len(ops) == 1 and ops[0].get('op') == 'set_string': man['member_span_max'] = 8192 + 2 * len(str(ops[0].get('value', '')))      # mirrors save._pending
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
if os.environ.get('EDIT_FLIP_WINDOW'):      # targeted: N byte flips of the DECOMPRESSED raw of each declared member INSIDE (+-32 B around) the edit's own diff window vs the source (valid re-encode), the spot the span rule cannot bound
    import cfb, rvtw, wlpart
    for pn, mem in (dm or {}).items():
        for mi in mem:
            ps = wlpart.Partition(rvtw.Stream(cfb.CFB(buf).streams()[pn].data)).mem[mi]['raw']
            c = cfb.CFB(good); st_ = rvtw.Stream(c.streams()[pn].data); pt = wlpart.Partition(st_); r = pt.mem[mi]['raw']
            if len(ps) != len(r):      # length-changing edit (c2x-rvtsave 105): the edit window is what is left after the common prefix and suffix
                m_ = min(len(ps), len(r)); pre = 0
                while pre < m_ and ps[pre] == r[pre]: pre += 1
                suf = 0
                while suf < m_ - pre and ps[len(ps) - 1 - suf] == r[len(r) - 1 - suf]: suf += 1
                d = [pre, max(pre, len(r) - suf - 1)]
            else: d = [i for i in range(len(r)) if r[i] != ps[i]]
            if not d: continue
            for t in range(int(os.environ['EDIT_FLIP_WINDOW'])):
                c = cfb.CFB(good); st_ = rvtw.Stream(c.streams()[pn].data); pt = wlpart.Partition(st_); r = pt.mem[mi]['raw']
                o = rnd.randrange(max(0, d[0] - 32), min(len(r), d[-1] + 33)); r[o] ^= 1 << rnd.randrange(8); pt.mem[mi]['dirty'] = True
                c.streams()[pn].data = st_.build(pt.rebuild(), keep_spare=False)
                tp = os.path.join(_T, 'rb.rvt'); cfb.write(c, tp); T['window_%s_%d_%d_at%d' % (pn.split('/')[-1], mi, t, o)] = open(tp, 'rb').read()
if os.environ.get('EDIT_FLIP_GLOBAL'):      # targeted: one byte flip in the stream data of every NON-partition stream the writer left unchanged (the gate tolerates Global/* when an edit is declared)
    import cfb
    sa_ = cfb.CFB(buf).streams()
    for sn in sorted(sa_):
        if sn.startswith('Partitions/'): continue
        c = cfb.CFB(good); d = bytearray(c.streams()[sn].data)
        if d != bytearray(sa_[sn].data) or not d: continue
        o = rnd.randrange(len(d)); d[o] ^= 1 << rnd.randrange(8); c.streams()[sn].data = bytes(d)
        tp = os.path.join(_T, 'gl.rvt'); cfb.write(c, tp); T['stream_%s_at%d' % (sn.replace('/', '_'), o)] = open(tp, 'rb').read()
if os.environ.get('EDIT_FLIP_CHANGEDGLOBAL'):      # targeted: byte flips (N per stream) inside every non-partition stream the writer DID change (e.g. Global/ElemTable on delete), where the frozen rule cannot help
    import cfb
    sa_ = cfb.CFB(buf).streams()
    for sn in sorted(sa_):
        if sn.startswith('Partitions/'): continue
        c = cfb.CFB(good); d0 = bytes(c.streams()[sn].data)
        if d0 == bytes(sa_[sn].data) or not d0: continue
        for t in range(int(os.environ['EDIT_FLIP_CHANGEDGLOBAL'])):
            c = cfb.CFB(good); d = bytearray(d0); o = rnd.randrange(len(d)); d[o] ^= 1 << rnd.randrange(8); c.streams()[sn].data = bytes(d)
            tp = os.path.join(_T, 'gc.rvt'); cfb.write(c, tp); T['changed_%s_%d_at%d' % (sn.replace('/', '_'), t, o)] = open(tp, 'rb').read()
if os.environ.get('EDIT_FLIP_ELEMTABLE_RAW'):      # crafted: flip a byte of the DECODED Global/ElemTable of the output and re-deflate it validly (survives inflate, so only a content check can see it)
    import cfb, zlib, rvtw
    for t in range(int(os.environ['EDIT_FLIP_ELEMTABLE_RAW'])):
        c = cfb.CFB(good); st_ = rvtw.Stream(c.streams()['Global/ElemTable'].data); P_ = bytes(st_.payload); i = P_.find(rvtw.GZ)
        do_ = zlib.decompressobj(-15); raw = bytearray(do_.decompress(P_[i + 10:])); tail_ = do_.unused_data      # gzip trailer: CRC32 + ISIZE + 6 more bytes; keep them, recompute CRC (an earlier version dropped them: every result was then a malformed stream, not a gate verdict)
        o = rnd.randrange(len(raw)); raw[o] ^= 1 << rnd.randrange(8)
        co = zlib.compressobj(6, zlib.DEFLATED, -15); z = co.compress(bytes(raw)) + co.flush()
        import struct; z += struct.pack('<II', zlib.crc32(bytes(raw)) & 0xffffffff, len(raw)) + tail_[8:]
        c.streams()['Global/ElemTable'].data = st_.build(P_[:i + 10] + z, keep_spare=False)
        tp = os.path.join(_T, 'et.rvt'); cfb.write(c, tp); T['elemtable_raw_%d_at%d_of%d' % (t, o, len(raw))] = open(tp, 'rb').read()
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
