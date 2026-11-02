"""c1x-native item 60: bytes appended after the end of the OLE/CFB file, then a real Comments edit + in-place SAVE!. Reports keep / drop / refuse; the original must never be damaged.
Autodesk 2024 template only (skips when absent)."""
import os, sys, tempfile, hashlib, shutil, json
_T = tempfile.mkdtemp(); HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvtfix/corpus/2024/71_Construction-DefaultMetric.rte')
if not os.path.exists(SRC): print('skip: no template'); sys.exit(0)
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')): sys.path.insert(0, p)
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w'))
os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', SAVEGATE_GATE=_T + '/gate.json')
import rvt_params
from rvtballet import save
save._import()
import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
g = lambda x: (x.get('params', x) if isinstance(x, dict) else {})
EID = next(e for e, d in rvt_params.params(SRC).items() if g(d).get('Comments') == '')
bad = 0
for name, junk in (('zeros512', b'\0' * 512), ('ctrlz_crlf', b'\x1a\r\n'), ('ff4k', b'\xff' * 4096)):
    d = tempfile.mkdtemp(dir=_T); p = d + '/s.rvt'; shutil.copy(SRC, p); open(p, 'ab').write(junk); h0 = sha(p); n0 = os.path.getsize(p)
    try:
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', p)
        save.add_edit(ss, 'm', p, {'op': 'set_string', 'eid': EID, 'param': 'Comments', 'value': 'junk-edit'})
        save.save_overwrite(ss, 'm', p); out = 'saved'
    except BaseException as e: out = 'refused:' + type(e).__name__ + ':' + str(e)[:90]
    h1 = sha(p); n1 = os.path.getsize(p)
    if out == 'saved':
        tail = open(p, 'rb').read()[-len(junk):]
        verdict = 'KEEP' if tail == junk else 'DROP'
        try: ok = g(rvt_params.params(p).get(EID, {})).get('Comments') == 'junk-edit'
        except Exception as e: ok = False
        if not ok: bad += 1
        print(name, out, verdict, 'size', n0, '->', n1, 'edit_visible', ok)
    else:
        if h1 != h0: bad += 1
        print(name, out, 'original untouched' if h1 == h0 else 'ORIGINAL CHANGED')
sys.exit(1 if bad else 0)
