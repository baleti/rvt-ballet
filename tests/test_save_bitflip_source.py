"""Read-write gap hunt: flip ONE byte at many offsets of a valid 2024 .rte, then in-place save with no edit. Allowed outcomes: refused with the file untouched, or accepted with output bytes == input (identity, damage not changed/hidden).
Forbidden: accepted and output differs from input (writer silently 'repaired' or re-encoded around damage), or source changed on refusal. Prints a count per outcome."""
import os, sys, tempfile, shutil, hashlib, random
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser(os.environ.get('FLIP_SRC', '~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte'))
N = int(os.environ.get('BITFLIPS', '12'))
from rvtballet import save
save._import()
import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
try:
    raw = open(RTE, 'rb').read(); rnd = random.Random(7); offs = sorted(rnd.randrange(int(os.environ.get('FLIP_LO', 512)), int(os.environ.get('FLIP_HI', len(raw)))) for _ in range(N)); res = {'refused': 0, 'identity': 0}; bad = []
    for o in offs:
        b = bytearray(raw); b[o] ^= 0x40; src = os.path.join(_T, 'x.rvt'); open(src, 'wb').write(bytes(b)); h = sha(src)
        try:
            ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src); save.save_overwrite(ss, 'm', src); ss.close()
            if sha(src) == h: res['identity'] += 1
            else: bad.append((o, 'accepted and output differs'))
        except Exception as e:
            if sha(src) == h: res['refused'] += 1
            else: bad.append((o, 'refused but source changed: %s' % type(e).__name__))
    print(res, 'offsets', offs[:6], '...'); assert not bad, bad; print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
