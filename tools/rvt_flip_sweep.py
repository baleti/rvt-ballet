"""ESCAPE sweep: N random single-bit flips in a file are handed to the gate as 'writer output' with an empty manifest. Every flip must be refused, or be PADDING_ONLY (all CFB streams byte-identical).
Anything else accepted = severity-1 ESCAPE. Aggregate output only.  usage: tools/rvt_flip_sweep.py FILE N [SEED]"""
import os, sys, tempfile, hashlib, shutil, random, collections, json
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab'))
from rvtballet import save
import cfb
src = os.path.join(_T, 'src.rvt'); shutil.copy(sys.argv[1], src); b = open(src, 'rb').read(); n = len(b); rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
streams = lambda x: {k: bytes(v.data) for k, v in cfb.CFB(x).streams().items()}; s0 = streams(b); ss = save.SaveSessions(); res = collections.Counter(); esc = []
for i in range(int(sys.argv[2])):
    o = rnd.randrange(n); x = bytearray(b); x[o] ^= 1 << rnd.randrange(8); x = bytes(x); dest = os.path.join(_T, 'o.rvt')
    try: save.save_as(ss, 'm', src, dest, new_bytes=x, manifest={'modified': []}); r = 'accepted'; os.remove(dest)
    except Exception as e: r = type(e).__name__
    if r == 'accepted':
        try: eq = streams(x) == s0
        except Exception: eq = False
        r = 'PADDING_ONLY' if eq else 'ESCAPE'
        if r == 'ESCAPE': esc.append(o)
    res[r] += 1
print(json.dumps({'n': n, 'results': dict(res), 'escape_offsets': esc[:10]}))
shutil.rmtree(_T, ignore_errors=True)
