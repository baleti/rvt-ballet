"""N random single set_string edits (MaterialElem), each: SAVE AS -> convert the output with the viewer pipeline -> compare the parameter table with the converted source:
exactly the rows of the edited element may differ and the edited value must be present. usage: tools/save_reload_check.py SRC.rvt MODELDIR_OF_SRC N SEED"""
import os, sys, tempfile, subprocess, sqlite3, random, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
from rvtballet import save
def table(d): return {(r[0], r[1]): r[2] for r in sqlite3.connect(os.path.join(d, 'model.sqlite')).execute('select e.id, p.k, p.v from prm p join el e on e.i=p.i')}
def main(src, md, n, seed):
    rnd = random.Random(seed); ids = [r[0] for r in sqlite3.connect(os.path.join(md, 'model.sqlite')).execute("select id from el where cls='MaterialElem' order by id")]
    base = table(md); ss = save.SaveSessions(); ss.doc('m', src); ok = bad = refused = 0; rows = []
    for k in range(n):
        eid = rnd.choice(ids); val = rnd.choice(['A', 'Ünï ✓', 'x' * 120, 'k-%d' % k]); ss.ed.clear()
        try: save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': eid, 'value': val, 'match': ''}); out = os.path.join(_T, 'o%d.rvt' % k); save.save_as(ss, 'm', src, out)
        except Exception as e: refused += 1; rows.append((eid, 'REFUSED ' + type(e).__name__)); continue
        r = subprocess.run([os.path.join(HERE, 'rvt-ballet'), 'convert', out, os.path.join(_T, 'c%d' % k)], capture_output=True, text=True, timeout=600)
        if r.returncode: bad += 1; rows.append((eid, 'CONVERT FAIL')); continue
        t = table(os.path.join(_T, 'c%d' % k)); diff = {x for x in base.keys() | t.keys() if base.get(x) != t.get(x)}
        good = diff and all(x[0] == eid for x in diff) and val in {t[x] for x in diff if x in t}
        ok += bool(good); bad += not good; rows.append((eid, 'OK' if good else 'BAD diff=%d other=%d' % (len(diff), sum(x[0] != eid for x in diff))))
        os.remove(out); import shutil; shutil.rmtree(os.path.join(_T, 'c%d' % k), ignore_errors=True)
        print(k, rows[-1], flush=True)
    print('RELOAD', json.dumps({'edits': n, 'ok': ok, 'bad': bad, 'refused': refused}))
main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
