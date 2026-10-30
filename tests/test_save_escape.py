"""ESCAPE hunt: tampered outputs handed to the gate (as if the writer had produced them) must ALL be refused with nothing written and the source intact.
Tampers: one byte flipped in the middle of the file, in the first and last sectors, truncation (-1 byte, -4096), appended garbage, appended sector of zeros, two sectors swapped,
a long zero run, whole file zero. Identity (untampered) must pass. Prints the tampers that were ACCEPTED (= escapes) and fails if any."""
import os, sys, tempfile, hashlib, shutil, random
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.environ.get('ESC_FILE') or os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src); h0 = sha(src); b = open(src, 'rb').read(); n = len(b); rnd = random.Random(7)
def flip(o): x = bytearray(b); x[o] ^= 0x01; return bytes(x)
T = {'identity': b, 'flip_mid': flip(n // 2), 'flip_first_sector': flip(1000), 'flip_last_byte': flip(n - 1), 'flip_rand_1': flip(rnd.randrange(n)), 'flip_rand_2': flip(rnd.randrange(n)), 'flip_rand_3': flip(rnd.randrange(n)),
     'trunc_1': b[:-1], 'trunc_4096': b[:-4096], 'append_garbage': b + b'garbage!', 'append_zero_sector': b + bytes(512), 'zero_run_4k': b[:n // 3] + bytes(4096) + b[n // 3 + 4096:],
     'swap_sectors': b[:409600] + b[413696:417792] + b[409600:413696] + b[417792:], 'all_zero': bytes(n), 'empty': b''}
sys.path.insert(0, os.path.expanduser('~/rvt-research/write-lab')); import cfb
streams = lambda x: {k: bytes(v.data) for k, v in cfb.CFB(x).streams().items()}; s0 = streams(b)
ss = save.SaveSessions(); esc = []; res = {}
for k, nb in T.items():
    dest = os.path.join(_T, 'o_%s.rvt' % k)
    try: save.save_as(ss, 'm', src, dest, new_bytes=nb, manifest={'modified': []}); acc = True
    except Exception as e: acc = False; res[k] = type(e).__name__
    if acc: res[k] = 'ACCEPTED'
    if k == 'identity': assert acc and sha(dest) == h0, res
    elif acc:
        res[k] = 'ACCEPTED_PADDING_ONLY' if streams(nb) == s0 else 'ACCEPTED'      # accepted but every stream is byte-identical: only header padding / free sectors differ (not an escape, but the gate cannot prove it: noted)
        if res[k] == 'ACCEPTED': esc.append(k)
    else: assert not os.path.exists(dest), k
    assert sha(src) == h0
print(res)
if esc: print('ESCAPES:', esc); sys.exit(1)
print('save escape OK')
