"""Two processes save two HARD-LINK names of one file at the same moment (different elements moved): each name is replaced atomically, both end as valid complete outputs equal to their own saver output (the link is broken, as the single-name case warns), no temp files"""
import os, sys, shutil, hashlib, tempfile, subprocess, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
W = r'''
import os, sys, json, time, hashlib
sys.path.insert(0, sys.argv[1]); from rvtballet import save, edit
p, eid, go, tag = sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
ss = save.SaveSessions(); d = ss.doc('m', p)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': eid, 'dx': 1.0})])
open(go + '.' + tag, 'w').close()
while not os.path.exists(go): time.sleep(0.005)
try: save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:%d' % eid]}); res = 'ok'
except Exception as e: res = type(e).__name__
print(json.dumps({'tag': tag, 'res': res, 'sha': hashlib.sha256(nb).hexdigest()}))
'''
if not os.path.exists(S): print('skip'); sys.exit(0)
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); env = dict(os.environ, SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', RVTBALLET_SNAPSHOT_CACHE=T + '/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', RVTBALLET_ALLOW_LAYOUT_CHANGE='1', SAVEGATE_GATE=T + '/gate.json')
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}')
p = T + '/m.rte'; q = T + '/n.rte'; shutil.copy(S, p); os.link(p, q); h0 = hashlib.sha256(open(p, 'rb').read()).hexdigest(); go = T + '/go'
procs = [subprocess.Popen([sys.executable, '-c', W, os.path.join(HERE, '..'), f, str(e), go, tag], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for f, e, tag in ((p, 301595, 'a'), (q, 301596, 'b'))]
for _ in range(1200):
    if os.path.exists(go + '.a') and os.path.exists(go + '.b'): break
    time.sleep(0.1)
open(go, 'w').close()
outs = {o['tag']: o for o in (json.loads(pr.communicate(timeout=600)[0].strip().splitlines()[-1]) for pr in procs)}
print({t: o['res'] for t, o in outs.items()})
sh = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()
for f, t in ((p, 'a'), (q, 'b')):
    if outs[t]['res'] == 'ok': assert sh(f) == outs[t]['sha'] != h0, 'file %s is not exactly its saver output' % t
    else: assert outs[t]['res'] in ('Locked', 'Conflict'), outs[t]; assert sh(f) in (h0, outs['a' if t == 'b' else 'b']['sha']), 'refused saver but its file is neither original nor the other output'
assert 'ok' in {o['res'] for o in outs.values()}
left = [f for f in os.listdir(T) if f.endswith(('.tmp', '.part', '.sgtmp', '.lock'))]; assert not left, left
print('hard-link names saved concurrently: outputs complete, no temp files')
