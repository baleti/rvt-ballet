"""edit -> SAVE AS -> convert the output with the viewer's own pipeline -> the inspector tables (model.sqlite prm) show the edited value on that element only,
same element count, source's converted table unchanged."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, tempfile, subprocess, sqlite3, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
def table(d):
    db = sqlite3.connect(os.path.join(d, 'model.sqlite')); return {(r[0], r[1]): r[2] for r in db.execute("select e.id, p.k, p.v from prm p join el e on e.i=p.i")}, db.execute('select count(*) from el').fetchone()[0]
def main():
    ss = save.SaveSessions(); ss.doc('m', RTE); save.add_edit(ss, 'm', RTE, {'op': 'set_string', 'eid': 24, 'value': 'Edited by test', 'match': ''})
    out = os.path.join(_T, 'e.rvt'); save.save_as(ss, 'm', RTE, out)
    for name, f in (('src', RTE), ('edited', out)):
        r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', f, os.path.join(_T, name)], capture_output=True, text=True, timeout=300); assert r.returncode == 0, r.stderr[-300:]
    (a, na), (b, nb) = table(_T + '/src'), table(_T + '/edited')
    assert na == nb, (na, nb)
    diff = {k for k in a.keys() | b.keys() if a.get(k) != b.get(k)}
    assert diff and all(k[0] == 24 for k in diff), sorted(diff)[:5]
    assert b[(24, 'Keynote')] == 'Edited by test' and a[(24, 'Keynote')] != b[(24, 'Keynote')]
    print('save reload OK: %d elements, %d parameter rows differ (all on element 24)' % (nb, len(diff)))
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip')
else: main()
