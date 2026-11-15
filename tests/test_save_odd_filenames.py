"""SAVE! in place of a source whose file name is odd (spaces, NFC/NFD accents, CJK, leading dash, 200 chars): saved bytes equal the edited bytes, the backup restores the original sha, no stray temp files stay next to it."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, shutil, hashlib, tempfile
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR'))
os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'
open(_T + '/gate.json', 'w').write('{"rvt": {"2024": "open"}}'); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save, edit
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
if not os.path.exists(S) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
import unicodedata
names = ['my model (copy) 1.rte', unicodedata.normalize('NFC', 'caf\u00e9 \u00fc.rte'), unicodedata.normalize('NFD', 'caf\u00e9 \u00fc.rte'), '\u65e5\u672c\u8a9e.rte', '-dash.rte', 'n' * 196 + '.rte', 'UPPER.RTE', 'noext', '.hidden.rte', 'trail .rte', 'a;b&c$d`e.rte']
for i, nm in enumerate(names):
    dd = _T + '/d%d' % i; os.makedirs(dd); a = os.path.join(dd, nm); shutil.copy(S, a); h0 = sha(a)
    ss = save.SaveSessions(); d = ss.doc('m%d' % i, a)
    nb, _ = edit.apply_full(d.buf, [edit.validate_op({'op': 'move', 'eid': 301595, 'dx': 1.0})])
    r = save.save_overwrite(ss, 'm%d' % i, a, new_bytes=nb, manifest={'modified': ['el:301595']})
    assert sha(a) == hashlib.sha256(nb).hexdigest(), 'saved bytes differ for %r' % nm
    left = [f for f in os.listdir(dd) if f not in (nm, '.savegate')]
    bk = [os.path.join(r0, f) for r0, _, fs in os.walk(dd + '/.savegate') for f in fs]
    assert any(sha(b) == h0 for b in bk), 'no backup with the original bytes for %r' % nm
    assert not left, 'stray files next to %r: %r' % (nm, left)
print('odd filename in-place save OK for', len(names), 'names')
