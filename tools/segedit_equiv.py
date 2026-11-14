"""segedit_equiv.py OUTJSONL FILE [N] [SEED]: equivalence sweep of the segment writer against the old full-model writer (no VM needed).
For N sampled FamilyInstance elements of FILE and each op (Mark set-string, move, rotate) run the OLD writer core (rvtballet.edit.apply_full, rvtedit backend:
the code the product's SAVE uses) and segedit in the shift layout on the same op, then compare every CFB stream. Verdicts per case:
  same          both wrote; every stream byte-identical (the segment writer reproduces the old output exactly)
  differ        both wrote; streams differ (BUG unless explained)
  both_refuse   both refused
  seg_refuse    old wrote, segedit refused (conservative: allowed, but counts against coverage)
  seg_only      segedit wrote, old refused (DANGER: investigate every one)
Aggregates only in shared notes; file names stay local."""
import sys, os, json, random, subprocess, tempfile, time
sys.path.insert(0, os.path.expanduser('~/src/rvt-ballet'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import olefile
from rvtballet import edit, segedit


def streams(b):
    import io
    o = olefile.OleFileIO(io.BytesIO(b) if isinstance(b, bytes) else b); return {'/'.join(e): o.openstream('/'.join(e)).read() for e in o.listdir(streams=True)}


def main():
    out, f = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 6; seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    els = json.loads(subprocess.run([sys.executable, '-m', 'rvtballet', 'elements', f, '--json'], capture_output=True, text=True, cwd=os.path.expanduser('~/src/rvt-ballet')).stdout)
    fi = [e['id'] for e in els if e['class'] == 'FamilyInstance']
    random.Random(seed).shuffle(fi); pick = fi[:n]
    src = open(f, 'rb').read(); S0 = streams(src)
    td = tempfile.mkdtemp(prefix='segeq-')
    for eid in pick:
        for op in (dict(op='set_string', eid=eid, param='Mark', value='seg-eq-%d' % eid), dict(op='move', eid=eid, dx=1.25, dy=-0.5, dz=0.0), dict(op='rotate', eid=eid, deg=30.0)):
            rec = dict(file=os.path.basename(f)[:2], eid=eid, op=op['op'])
            t0 = time.time()
            try:
                vo = edit.validate_op(dict(op, **({'dz': 0.0} if op['op'] == 'move' else {})))
                ob, _ = edit.apply_full(src, [vo]); old_err = None
            except Exception as e: ob = None; old_err = '%s: %s' % (type(e).__name__, str(e)[:160])
            rec['old_s'] = round(time.time() - t0, 1); t0 = time.time()
            dst = os.path.join(td, 'seg_%d_%s.rvt' % (eid, op['op']))
            try:
                info = segedit.apply_ops(f, dst, [op], mode='shift'); sb = open(dst, 'rb').read(); os.remove(dst); seg_err = None
            except segedit.Refused as e: sb = None; seg_err = 'Refused: %s' % str(e)[:160]
            except Exception as e: sb = None; seg_err = '%s: %s' % (type(e).__name__, str(e)[:160])
            rec['seg_s'] = round(time.time() - t0, 1)
            if ob is not None and sb is not None:
                A, B = streams(ob), streams(sb); d = sorted(k for k in set(A) | set(B) if A.get(k) != B.get(k))
                rec['verdict'] = 'same' if not d else 'differ'; rec['differ_streams'] = d
                rec['changed_vs_src'] = sorted(k for k in A if A[k] != S0.get(k))
            elif ob is None and sb is None: rec['verdict'] = 'both_refuse'
            elif ob is not None: rec['verdict'] = 'seg_refuse'
            else: rec['verdict'] = 'seg_only'
            rec['old_err'] = old_err; rec['seg_err'] = seg_err
            print(json.dumps(rec), flush=True)
            with open(out, 'a') as fh: fh.write(json.dumps(rec) + '\n')


if __name__ == '__main__':
    main()
