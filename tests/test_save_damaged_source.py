"""c1x-native item 65: damaged copies of the Autodesk 2024 template (5/40/400 byte flips, truncations, 3 seeds each) -> Comments edit + in-place SAVE!. Per case: REFUSED with the file byte-untouched, or SAVED and the output re-reads (params readable);
a SAVED output that cannot be re-read, a changed file after a refusal, or a hang (300 s) is a failure. Prints counts."""
import os, sys, tempfile, hashlib, shutil, json, random, subprocess, collections
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(SRC): print('skip: no template'); sys.exit(0)
CHILD = r'''
import os, sys, json, hashlib
sys.path.insert(0, %(here)r)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
import rvt_params
from rvtballet import save
save._import()
import savegate as sg
p, eid = sys.argv[1], int(sys.argv[2])
try:
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', p)
    save.add_edit(ss, 'm', p, {'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': 'dmg-edit'}); save.save_overwrite(ss, 'm', p); print('SAVED')
except BaseException as e: print('REFUSED', type(e).__name__, str(e)[:70].replace(chr(10), ' '))
'''
T = tempfile.mkdtemp(); gate = T + '/gate.json'; json.dump({'rvt': {'2024': 'open'}}, open(gate, 'w'))
ENV = dict(os.environ, SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=gate)
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
os.environ.update(ENV)
import rvt_params
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
EID = next(e for e, d in rvt_params.params(SRC).items() if g(d).get('Comments') == '')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
b = open(SRC, 'rb').read(); C = collections.Counter(); bad = []
for seed in (1, 2, 3):
    random.seed(seed)
    for mode in ('flip5', 'flip40', 'flip400', 'trunc'):
        c = bytearray(b)
        if mode == 'trunc': c = c[:random.randint(1000, len(c) - 1)]
        else:
            for _ in range(int(mode[4:])): c[random.randrange(len(c))] ^= 1 << random.randrange(8)
        p = '%s/%s_%d.rvt' % (T, mode, seed); open(p, 'wb').write(c); h0 = sha(p)
        try: r = subprocess.run([sys.executable, '-c', CHILD % {'here': HERE}, p, str(EID)], env=ENV, capture_output=True, text=True, timeout=300); out = (r.stdout.strip().splitlines() or ['CRASH rc%d' % r.returncode])[-1]
        except subprocess.TimeoutExpired: out = 'HANG'
        if out.startswith('REFUSED'): C['refused'] += 1; ok = sha(p) == h0; print(mode, seed, out)
        elif out == 'SAVED':
            try: rvt_params.params(p); ok = True
            except Exception: ok = False
            C['saved'] += 1
        else: C[out.split()[0]] += 1; ok = False
        if not ok: bad.append((mode, seed, out))
print(dict(C), 'FAILURES', bad); sys.exit(1 if bad else 0)
