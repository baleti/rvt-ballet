"""Bit-flip / truncate / pad a source RVT, then no-edit SAVE AS. Expectation: refused, or output bytes == damaged source. Anything else is an ESCAPE.
usage: tools/rvtwrite_flip.py SRC.rvt N [seed]   (aggregate output only)"""
import os, sys, tempfile, shutil, random, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
ss = save.SaveSessions(); raw = open(sys.argv[1], 'rb').read(); n = int(sys.argv[2]); rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
res = {'same': 0, 'refused': 0, 'ESCAPE': 0}; kinds = {}
for k in range(n):
    b = bytearray(raw); m = rnd.choice(['flip', 'flip8', 'trunc', 'pad', 'zero'])
    if m == 'flip': b[rnd.randrange(len(b))] ^= 1 << rnd.randrange(8)
    elif m == 'flip8':
        for _ in range(8): b[rnd.randrange(len(b))] ^= 0xFF
    elif m == 'trunc': b = b[:rnd.randrange(512, len(b))]
    elif m == 'pad': b += bytes(rnd.randrange(1, 4096))
    else:
        o = rnd.randrange(len(b) - 600); b[o:o + 512] = bytes(512)
    src = _T + '/s.rvt'; dst = _T + '/o.rvt'; open(src, 'wb').write(b); h = bytes(b)
    try:
        save.save_as(ss, 'm%d' % k, src, dst); ok = open(dst, 'rb').read() == h; res['same' if ok else 'ESCAPE'] += 1
        if not ok: kinds[m] = kinds.get(m, 0) + 1; shutil.copy(src, _T + '/escape%d.rvt' % k)
    except Exception as e: res['refused'] += 1
    assert open(src, 'rb').read() == h, 'SOURCE MODIFIED'
    os.path.exists(dst) and os.remove(dst)
print(json.dumps({'res': res, 'escape_kinds': kinds, 'tmp': _T if res['ESCAPE'] else None}))
if not res['ESCAPE']: shutil.rmtree(_T, ignore_errors=True)
