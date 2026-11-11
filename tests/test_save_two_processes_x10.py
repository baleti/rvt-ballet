"""x10 with a random start offset (0..400 ms) for process b: same assertions. Original: Two separate processes (two viewers) load the same file, each moves a DIFFERENT element and both save in place at the same moment: no lost update and no corruption. Expected: exactly one saves, the other gets Locked or Conflict; the file equals the winner's output byte for byte and opens in the reader."""
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
time.sleep(float(os.environ.get('DELAY_' + tag, '0')))
try: save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:%d' % eid]}); res = 'ok'
except Exception as e: res = type(e).__name__
print(json.dumps({'tag': tag, 'res': res, 'sha': hashlib.sha256(nb).hexdigest()}))
'''
if not os.path.exists(S): print('skip'); sys.exit(0)
T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); env = dict(os.environ, SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', RVTBALLET_SNAPSHOT_CACHE=T + '/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', RVTBALLET_ALLOW_LAYOUT_CHANGE='1', SAVEGATE_GATE=T + '/gate.json')
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}')
import random
R = random.Random(int(os.environ.get('SEED', '5'))); tally = {}
for it in range(10):
    p = T + '/m%d.rte' % it; shutil.copy(S, p); h0 = hashlib.sha256(open(p, 'rb').read()).hexdigest(); go = T + '/go%d' % it
    d = R.random() * 0.4
    envs = [dict(env, DELAY_a='0', DELAY_b='%.3f' % d)] * 2
    procs = [subprocess.Popen([sys.executable, '-c', W, os.path.join(HERE, '..'), p, str(e), go, tag], env=env2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for (e, tag), env2 in zip(((301595, 'a'), (301596, 'b')), envs)]
    for _ in range(1200):
        if os.path.exists(go + '.a') and os.path.exists(go + '.b'): break
        time.sleep(0.1)
    open(go, 'w').close()
    outs = [json.loads(pr.communicate(timeout=600)[0].strip().splitlines()[-1]) for pr in procs]
    res = sorted(o['res'] for o in outs); win = [o for o in outs if o['res'] == 'ok']
    tally[tuple(res)] = tally.get(tuple(res), 0) + 1
    assert res in (['Conflict', 'ok'], ['Locked', 'ok']), (it, d, outs)
    assert hashlib.sha256(open(p, 'rb').read()).hexdigest() == win[0]['sha'] != h0, 'file is not exactly the winner output'
left = [f for f in os.listdir(T) if f.endswith(('.tmp', '.part', '.sgtmp', '.lock'))]; assert not left, left
print('10 races with random offsets: one saved each time, file == winner output, no temp files', tally)
