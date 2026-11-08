"""c1x-rvtsave 225: 4 processes save DIFFERENT files at the same time sharing one journal/cache/backup dir: every file ends with its own edit (own marker in Comments), none has another's, no temp files left. Autodesk 2024 Construction template copies."""
import os, sys, tempfile, shutil, subprocess, json
HERE = os.path.dirname(os.path.abspath(__file__)); S = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
T = tempfile.mkdtemp(); json.dump({'rvt': {'2024': 'open'}}, open(T + '/gate.json', 'w'))
CHILD = '''
import os, sys
sys.path.insert(0, %r); sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab')]
import rvt_params
from rvtballet import save
save._import()
import savegate as sg
p, eid, v = sys.argv[1], int(sys.argv[2]), sys.argv[3]
ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', p)
save.add_edit(ss, 'm', p, {'op': 'set_string', 'eid': eid, 'param': 'Comments', 'value': v}); save.save_overwrite(ss, 'm', p); print('saved')
''' % os.path.join(HERE, '..')
env = dict(os.environ, SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', SAVEGATE_BACKUPS=T + '/b', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=T + '/gate.json')
sys.path[:0] = [os.path.expanduser(p) for p in ('~/rvt-research', '~/rvt-research/write-lab')]
import rvt_params
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
E = next(e for e, d in rvt_params.params(S).items() if g(d).get('Comments') == '')
ps = []
for i in range(4):
    p = '%s/f%d.rte' % (T, i); shutil.copy(S, p)
    ps.append((p, 'marker-%d' % i, subprocess.Popen([sys.executable, '-c', CHILD, p, str(E), 'marker-%d' % i], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)))
bad = 0
for p, m, pr in ps:
    out = pr.communicate()[0]; got = g(rvt_params.params(p)[E]).get('Comments'); ok = pr.returncode == 0 and got == m
    print(os.path.basename(p), 'rc', pr.returncode, 'comment', got, 'OK' if ok else 'BAD ' + out[-200:]); bad += not ok
left = [f for f in os.listdir(T) if 'sgtmp' in f]; assert not left, left
shutil.rmtree(T, ignore_errors=True); assert not bad; print('OK')
