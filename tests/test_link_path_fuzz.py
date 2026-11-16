"""c1x-rvtlink item 107: seeded random valid link paths (1..120 chars, BMP + non-BMP, spaces inside) written by set_link_path and read back from the OUTPUT bytes equal the value; nothing refused unexpectedly. Seed ~/c5x-link/al/seed.rvt (skipped if absent)."""
import os, sys, random, struct, tempfile
SEED = os.path.expanduser('~/c5x-link/al/seed.rvt')
if not os.path.exists(SEED): print('SKIP: no seed'); sys.exit(0)
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ENABLE_LINKPATH'] = '1'
import rvtedit
from rvtballet import edit
buf = open(SEED, 'rb').read(); rnd = random.Random(int(os.environ.get('SEED', '7')))
alpha = 'abcXYZ019_-()[]{}#&@!%+=,;~äüß中文Ж\U0001F600 '
def readback(b):
    f = tempfile.NamedTemporaryFile(suffix='.rvt', delete=False); f.write(b); f.close()
    try:
        ed = rvtedit.Edit(f.name); ls = [l for l in ed.g.e.trace(1363937)[3] if l[1] == 'ModelPath.m_path']
        bd = edit._body(ed, 1363937); n = struct.unpack_from('<I', bd, ls[0][2])[0]
        return bytes(bd[ls[0][2] + 4:ls[0][2] + 4 + 2 * n]).decode('utf-16le')
    finally: os.unlink(f.name)
N = int(os.environ.get('N', '6'))
for i in range(N):
    segs = [''.join(rnd.choice(alpha) for _ in range(rnd.randint(1, 30))).strip(' .') or 'x' for _ in range(rnd.randint(1, 3))]
    v = '\\'.join(segs) + '.rvt'
    try: out = edit.apply(buf, [{'op': 'set_link_path', 'eid': 1363937, 'value': v}])
    except edit.EditError as e: print('REFUSED', repr(v), str(e)[:90]); continue
    out = out[0] if isinstance(out, tuple) else out
    got = readback(out); assert got == v, (v, got)
    print('ok', len(v))
print('OK fuzz')
