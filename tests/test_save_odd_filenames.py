"""In-place SAVE! + restore on odd file names (leading dash, newline, quote, $(), backtick, semicolon, leading dot, trailing space): saved bytes verified, backup restores the original byte-exact, no debris beside the file."""
import os, sys, shutil, hashlib, tempfile
T = tempfile.mkdtemp(dir=os.path.expanduser('~'))
os.environ['SAVEGATE_JOURNAL'] = T + '/j'; os.environ['SAVEGATE_CACHE'] = T + '/c'; os.environ['SAVEGATE_BACKUPS'] = 'cache'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
open(T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest(); h0 = sha(S)
NAMES = ['-dash.rte', 'new\nline.rte', "q'uote\".rte", '$(touch PWNED).rte', '`touch PWNED`.rte', 'semi;colon&amp.rte', '.hidden.rte', 'trail .rte', '*glob?.rte']
try:
    for i, n in enumerate(NAMES):
        D = T + '/d%d' % i; os.mkdir(D); p = D + '/' + n; shutil.copy(S, p)
        ss = save.SaveSessions(); d = ss.doc('m%d' % i, p)
        nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
        save.save_overwrite(ss, 'm%d' % i, p, new_bytes=nb, manifest={'modified': ['el:301595']})
        assert sha(p) != h0, n
        save.restore_backup(ss, 'm%d' % i, p, 0); assert sha(p) == h0, 'restore not exact for %r' % n
        left = sorted(os.listdir(D)); assert left == [n], 'debris %r' % left
    assert not os.path.exists('PWNED') and not any('PWNED' in f for f in os.listdir(T))
    print('odd file names OK:', len(NAMES))
finally: shutil.rmtree(T, True)
