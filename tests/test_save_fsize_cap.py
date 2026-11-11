"""File-size cap (RLIMIT_FSIZE, stand-in for a full disk) smaller than the output: in-place SAVE! must fail, original byte-identical, no debris; after lifting the cap SAVE! works. Original: In-place SAVE! + restore on odd file names (leading dash, newline, quote, $(), backtick, semicolon, leading dot, trailing space): saved bytes verified, backup restores the original byte-exact, no debris beside the file."""
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.path.expanduser('~'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['SAVEGATE_BACKUPS'] = 'cache'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); h0 = sha(S)
import resource, signal
signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
D = T + '/d'; os.mkdir(D); p = D + '/m.rte'; shutil.copy(S, p)
ss = save.SaveSessions(); d = ss.doc('m', p)
nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
try:
    sz = os.path.getsize(p)
    for frac in (0.9, 0.5, 0.01):
        resource.setrlimit(resource.RLIMIT_FSIZE, (int(sz * frac), resource.RLIM_INFINITY))
        try: save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']}); res = 'SAVED'
        except Exception as e: res = type(e).__name__
        resource.setrlimit(resource.RLIMIT_FSIZE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        print('cap %.2f x size ->' % frac, res)
        assert res != 'SAVED' and sha(p) == h0, 'cap %.2f: saved or original changed (%s)' % (frac, res)
        left = sorted(f for f in os.listdir(D) if f != 'm.rte'); assert not left, left
    save.save_overwrite(ss, 'm', p, new_bytes=nb, manifest={'modified': ['el:301595']}); assert sha(p) != h0
    print('size-capped saves refused, original intact; after lifting the cap the save works')
finally:
    resource.setrlimit(resource.RLIMIT_FSIZE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)); shutil.rmtree(T, True)
