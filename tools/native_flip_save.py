"""native_flip_save.py SRC N SEED: N trials, each flips one random byte (or truncates, every 4th trial) of a copy of SRC, no-edit SAVE AS with the native rvt_core path. Result per trial must be identical-bytes / clean refusal (a classified exception); a crash of the process, a partial dst, or a dst that differs from the damaged source is a failure. Aggregate output."""
import os, sys, tempfile, shutil, random, collections, subprocess, json
if len(sys.argv) > 4 and sys.argv[4] == 'child':
    _T = sys.argv[5]; os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from rvtballet import save
    ss = save.SaveSessions(); src, dst = _T + '/s.rvt', _T + '/o.rvt'
    try:
        save.save_as(ss, 'm', src, dst)
        print('SAVED', 'same' if open(src, 'rb').read() == open(dst, 'rb').read() else 'DIFFERENT')
    except Exception as e: print('REFUSED', type(e).__name__, os.path.exists(dst))
    sys.exit(0)
src, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); r = random.Random(seed); b = open(src, 'rb').read(); tot = collections.Counter()
for t in range(n):
    T = tempfile.mkdtemp(); x = bytearray(b)
    if t % 4 == 3: x = x[:r.randrange(1, len(x))]
    else: x[r.randrange(len(x))] ^= 1 << r.randrange(8)
    open(T + '/s.rvt', 'wb').write(x)
    p = subprocess.run([sys.executable, __file__, src, '0', '0', 'child', T], capture_output=True, text=True, timeout=300)
    last = (p.stdout.strip().splitlines() or ['NOOUT'])[-1]
    k = 'CRASH rc=%d' % p.returncode if p.returncode else last.split(' ')[0] + (' leftover' if last.endswith('True') else '') + (' DIFF' if 'DIFFERENT' in last else '')
    tot[k] += 1; shutil.rmtree(T, True)
print(dict(tot))
