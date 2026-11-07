"""c1x-native item 61: hostile strings in a Comments edit + in-place SAVE!: saved and read back equal, or cleanly refused with the original untouched.
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
CASES = (('cjk', '\u6f22\u5b57\u304b\u306a\ud55c\uae00'), ('emoji', 'x\U0001F600y'), ('umlaut', '\u00e4\u00f6\u00fc\u00df\u00e9'), ('long5000', 'A' * 5000), ('newline', 'a\nb\r\nc\td'), ('nul', 'a\x00b'), ('surrogate', 'a\ud800b'), ('quote', 'a"b\'c<>&\\'), ('nfd', 'e\u0301a\u0308'), ('bom_rlo', '\ufeffx\u202ey'), ('long70k', 'B' * 70000))
for name, val in CASES:
    d = tempfile.mkdtemp(dir=_T); p = d + '/s.rvt'; shutil.copy(SRC, p); h0 = sha(p)
    try:
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', p)
        save.add_edit(ss, 'm', p, {'op': 'set_string', 'eid': EID, 'param': 'Comments', 'value': val})
        save.save_overwrite(ss, 'm', p); out = 'saved'
    except BaseException as e: out = 'refused:' + type(e).__name__ + ':' + str(e)[:80]
    if out == 'saved':
        try: back = g(rvt_params.params(p).get(EID, {})).get('Comments')
        except Exception as e: back = 'ERR ' + str(e)[:40]
        ok = back == val
        if not ok: bad += 1
        print(name, 'saved', 'roundtrip_equal' if ok else 'MISMATCH %r' % (back[:30] if isinstance(back, str) else back))
    else:
        if sha(p) != h0: bad += 1
        print(name, out, 'original untouched' if sha(p) == h0 else 'ORIGINAL CHANGED')
sys.exit(1 if bad else 0)
