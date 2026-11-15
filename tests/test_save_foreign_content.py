"""A source that is not a Revit file (DWG-like header, PNG, ZIP, text, random, a CFB container that lacks the Revit streams) named .rvt: any edit/save is refused and the file is byte-identical afterwards, no temp or backup litter next to it."""
import os, sys, tempfile, shutil, hashlib
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(RTE): print('skipped (scene missing)'); sys.exit(0)
T = tempfile.mkdtemp()
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import save, edit
save._import(); import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
real = open(RTE, 'rb').read()
cfb_head = real[:512]          # real CFB header, body cut: streams missing
cases = {'dwg': b'AC1032' + os.urandom(20000), 'png': b'\x89PNG\r\n\x1a\n' + os.urandom(9000), 'zip': b'PK\x03\x04' + os.urandom(9000),
         'text': b'hello world\n' * 500, 'random': os.urandom(30000), 'cfbhead': cfb_head, 'cfbhalf': real[:len(real) // 2], 'zeros': b'\0' * 8192}
bad = 0
try:
    for n, data in cases.items():
        d = tempfile.mkdtemp(dir=T); src = d + '/x.rvt'; open(src, 'wb').write(data); h = sha(src)
        try:
            ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); dd = ss.doc('m', src)
            nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
            save.save_overwrite(ss, 'm', src, new_bytes=nb, manifest={'modified': ['el:301595']}); res = 'ACCEPTED'
        except Exception as e: res = 'refused ' + type(e).__name__
        same = sha(src) == h; litter = os.listdir(d)
        ok = res != 'ACCEPTED' and same and litter == ['x.rvt']
        print(n, res, 'same=%s' % same, 'litter=%s' % [x for x in litter if x != 'x.rvt']); bad += not ok
    assert not bad, 'foreign content accepted or file touched'; print('OK')
finally: shutil.rmtree(T, ignore_errors=True)
