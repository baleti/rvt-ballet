"""ESCAPE hunt for change_type: take a correct change_type output (OUT.rvt from tools/rvt_change_type_save.py), flip ONE bit at N random positions, hand each to the gate with the true manifest (modified = the one instance). Every flipped output must be refused, source intact.
usage: tools/rvt_changetype_flip.py SRC.rvt OUT.rvt INSTANCE_EID N SEED   (Autodesk samples only; aggregate output)"""
import os, sys, tempfile, hashlib, shutil, random, json
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_SNAPSHOT_CACHE=_T + '/snap', RVTBALLET_EDIT_BACKEND='rvtedit')
import atexit; atexit.register(shutil.rmtree, _T, True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
json.dump({'rvt': {str(y): 'open' for y in range(2015, 2030)}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
from rvtballet import save
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
src0, out, inst, n, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
src = os.path.join(_T, 'src.rvt'); shutil.copy(src0, src); h0 = sha(src); good = open(out, 'rb').read(); rnd = random.Random(seed); ss = save.SaveSessions(); man = json.loads(os.environ['MAN_JSON']) if os.environ.get('MAN_JSON') else {'modified': ['el:%d' % inst]}      # MAN_JSON overrides the manifest, e.g. {"added": ["el:1542917", "el:1542918"]} for a duplicate-type output
if os.environ.get('DM_JSON'): man['dirty_members'] = json.loads(os.environ['DM_JSON'])      # e.g. {"Partitions/21": [41]}: what the writer reports as rewritten (edit.last_dirty_members)
T = {'control_true_output': good}
for k in range(n):
    o = rnd.randrange(len(good)); x = bytearray(good); x[o] ^= 1 << rnd.randrange(8); T['flip_%d' % k] = bytes(x)
if os.environ.get('ONLY'): T = {k: v for k, v in T.items() if k in ('control_true_output',) + tuple('flip_%s' % i for i in os.environ['ONLY'].split(','))} if os.environ.get('WITH_CONTROL') else {k: v for k, v in T.items() if k in tuple('flip_%s' % i for i in os.environ['ONLY'].split(','))}
if os.environ.get('TRACE'):
    from savegate.adapters import RvtAdapter as _R; _o = _R.extra_checks
    def _t(self, manifest): r = _o(self, manifest); print('TRACE extra_checks dm=%s bufs=%s -> %s' % (manifest.get('dirty_members'), len(getattr(self, '_verify_bufs', None) or ()), str(r)[:200]), flush=True); return r
    _R.extra_checks = _t
res = {}; esc = []
for k, nb in T.items():
    dest = os.path.join(_T, 'o_%s.rvt' % k)
    try: save.save_as(ss, 'm', src, dest, new_bytes=nb, manifest=man); acc = True
    except Exception as e: acc = False; res[k] = type(e).__name__
    if acc:
        res[k] = 'ACCEPTED'
        if k != 'control_true_output': esc.append(k)
    elif k != 'control_true_output': assert not os.path.exists(dest), k
    assert sha(src) == h0
    print(k, res[k], flush=True)
print('ESCAPES' if esc else 'no escapes', esc, 'n=%d' % n)
