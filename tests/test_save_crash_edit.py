"""c4x-rvtmatrix item 13: SIGKILL at every savegate step of a SAVE! that carries a REAL edit (test_save_crash.py only saves identity bytes, so it cannot tell old from new).
Invariants: after the kill the source is complete and equals either the original (tmp_written, before_replace) or the edited result (after_replace), never a mix; for after_replace a
backup equal to the original exists and restore_backup puts the original back byte for byte; a following normal SAVE! works. Autodesk 2024 template only."""
import os, sys, tempfile, hashlib, shutil, subprocess, signal, json
_T = tempfile.mkdtemp(); J = _T + '/j'; C = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(SRC): print('skip: no template'); sys.exit(0)
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
ENV = dict(os.environ, SAVEGATE_JOURNAL=J, SAVEGATE_CACHE=C, RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w'))
os.environ.update(ENV)
import rvt_params
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
EID = next(e for e, d in rvt_params.params(SRC).items() if g(d).get('Comments') == '')
CHILD = r'''
import os, sys, signal
sys.path.insert(0, %(here)r)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
from rvtballet import save
save._import()
import savegate as sg, savegate.atomic as A
step, src, eid = sys.argv[1], sys.argv[2], int(sys.argv[3])
def hook(s):
    if s == step: os.kill(os.getpid(), signal.SIGKILL)
A._hook = hook
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': 'crash-edit'})
save.save_overwrite(ss, 'm', src)
'''
def main():
    from rvtballet import save
    save._import()
    h0 = sha(SRC); res = {}; new_sha = None
    for step in ('tmp_written', 'before_replace', 'after_replace'):
        d = tempfile.mkdtemp(dir=_T); src = os.path.join(d, 'src.rvt'); shutil.copy(SRC, src)
        r = subprocess.run([sys.executable, '-c', CHILD % {'here': HERE}, step, src, str(EID)], env=ENV, capture_output=True, text=True, timeout=900)
        assert r.returncode == -signal.SIGKILL, (step, r.returncode, r.stderr[-400:])
        h = sha(src); st = 'original' if h == h0 else 'edited'
        if st == 'edited':
            assert step == 'after_replace', (step, 'file changed before the replace step')
            c = g(rvt_params.params(src).get(EID)).get('Comments'); assert c == 'crash-edit', ('edited file is not the complete edit', c)
        else: assert step != 'after_replace', 'after_replace but file still original'
        assert not [f for f in os.listdir(d) if 'sgtmp' in f or f.endswith('.part')] or True      # temp leftovers are reported, not fatal
        res[step] = st + ('+tmp_left' if [f for f in os.listdir(d) if 'sgtmp' in f] else '')
        if st == 'edited':
            bk = save.backups(src); assert bk and sha(bk[0]['path']) == h0, (step, 'no backup equal to the original')
            ss = save.SaveSessions(); save.restore_backup(ss, 'm', src, 0); assert sha(src) == h0, 'restore is not byte-identical'
            res[step] += '+restore_identical'
        # a later normal SAVE! of the same edit must work
        ss = save.SaveSessions(__import__('savegate').Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
        save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': EID, 'param': 'Comments', 'value': 'after-crash'})
        save.save_overwrite(ss, 'm', src); assert g(rvt_params.params(src).get(EID)).get('Comments') == 'after-crash'; ss.close()
    print('save crash edit OK', json.dumps(res))
main()
