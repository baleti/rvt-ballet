"""c6x-rvtmatrix (new corruption angle): in-place edit+SAVE! on a source whose path has spaces, quotes, CJK and accents (backup name, journal and temp file must cope), and a DIRECTORY named x.rvt must be refused without touching anything. Autodesk 2024 Construction template."""
import os, sys, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(SRC): print('skip: no template'); sys.exit(0)
for p in ('~/rvt-research', '~/rvt-research/write-lab', '~/rvt-research/edit-lab'): sys.path.insert(0, os.path.expanduser(p))
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w'))
os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
import rvt_params
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
EID = next(e for e, d in rvt_params.params(SRC).items() if g(d).get('Comments') == '')
from rvtballet import save
save._import()
import savegate as sg
h0 = sha(SRC)
try:
    d = os.path.join(_T, "my 'quoted' dir 日本語 éü; x"); os.makedirs(d)
    src = os.path.join(d, "modèle 漢字 (v2) 'a' & b.rvt"); shutil.copy(SRC, src)
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
    save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': EID, 'param': 'Comments', 'value': 'odd-path'})
    save.save_overwrite(ss, 'm', src)
    assert sha(src) != h0
    left = sorted(os.listdir(d)); print('saved in odd path; dir now:', len(left), 'entries')
    assert not [f for f in left if f.endswith(('.tmp', '.part')) or '.sgtmp' in f], left
    bk = [f for f in left if f != os.path.basename(src)]; print('backup entries:', len(bk)); assert len(bk) == 1, left
    P = rvt_params.params(src); assert g(P[EID]).get('Comments') == 'odd-path'
    # a directory named *.rvt
    dd = os.path.join(_T, 'dir.rvt'); os.makedirs(dd); open(dd + '/f', 'wb').write(b'x')
    try:
        ss2 = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss2.doc('m2', dd)
        save.add_edit(ss2, 'm2', dd, {'op': 'set_string', 'eid': EID, 'param': 'Comments', 'value': 'x'}); save.save_overwrite(ss2, 'm2', dd)
        raise SystemExit('FAIL: directory accepted as source')
    except SystemExit: raise
    except Exception as e: print('directory source refused:', type(e).__name__)
    assert os.path.isdir(dd) and os.listdir(dd) == ['f'] and open(dd + '/f', 'rb').read() == b'x'
    print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
