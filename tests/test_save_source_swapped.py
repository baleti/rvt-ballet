"""Source replaced by a DIFFERENT valid file (same name, mtime restored) between edit and SAVE!: the save must refuse (the edit was computed from other bytes) and leave the replacement byte-identical; it must never write the old file's edited bytes over it."""
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.path.expanduser('~'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['SAVEGATE_BACKUPS'] = 'cache'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
D = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/')
S = D + '2024_writer_cols2.rte'; OTHER = [D + f for f in sorted(os.listdir(D)) if f.startswith('2024_') and f.endswith('.rte') and D + f != S] if os.path.isdir(D) else []
if not os.path.exists(S) or not OTHER or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
try:
    p = T + '/m.rte'; shutil.copy(S, p); st = os.stat(p)
    ss = save.SaveSessions(); d = ss.doc('m', p)
    nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
    shutil.copy(OTHER[0], p); os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns)); h1 = sha(p)
    try: save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']}); res = 'saved'
    except Exception as e: res = 'refused:%s' % type(e).__name__
    now = sha(p)
    assert res != 'saved' and now == h1, 'swapped source was overwritten with edited bytes of the old file (%s)' % res
    print('swapped source ->', res, ', replacement intact')
finally: shutil.rmtree(T, True)
