"""c1x-rvtsave 227: in-place SAVE! with the savegate file in each bad state (year closed, year missing, empty file, malformed JSON, gate file absent, unknown state string): gated save is refused and the original is byte-identical; with state 'open' it saves. Synthetic 2024 .rte."""
import os, sys, tempfile, shutil, hashlib, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S): print('skip'); sys.exit(0)
T = tempfile.mkdtemp()
os.environ.update(SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', SAVEGATE_BACKUPS=T + '/b', RVTBALLET_SNAPSHOT_CACHE=T + '/s', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ALLOW_OVERWRITE='1', RVTBALLET_ALLOW_LAYOUT_CHANGE='1', SAVEGATE_GATE=T + '/gate.json')
from rvtballet import save, edit
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
STATES = {'closed': '{"rvt": {"2024": "closed"}}', 'year_missing': '{"rvt": {"2025": "open"}}', 'empty': '', 'malformed': '{"rvt": ', 'absent': None, 'unknown': '{"rvt": {"2024": "maybe"}}', 'open': '{"rvt": {"2024": "open"}}'}
bad = 0
for name, txt in STATES.items():
    if txt is None:
        if os.path.exists(T + '/gate.json'): os.remove(T + '/gate.json')
    else: open(T + '/gate.json', 'w').write(txt)
    p = T + '/f_%s.rte' % name; shutil.copy(S, p); h0 = sha(p)
    try:
        ss = save.SaveSessions(); dd = ss.doc('m', p)
        nb, _ = edit.apply_full(dd.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
        save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']}); res = 'saved'
    except Exception as e: res = 'refused ' + type(e).__name__
    changed = sha(p) != h0; ok = (res == 'saved' and changed) if name == 'open' else (res != 'saved' and not changed)
    print(name, res, 'file changed' if changed else 'file intact', 'OK' if ok else 'BAD'); bad += not ok
shutil.rmtree(T, ignore_errors=True); assert not bad; print('OK')
