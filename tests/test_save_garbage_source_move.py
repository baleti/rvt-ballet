"""save of a move on a source that is not a usable .rvt (zeros, text, truncated real file): refused with an exception at load/edit/save, source bytes untouched, SAVE AS target absent."""
import os, sys, tempfile, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
from rvtballet import save
save._import()
import savegate as sg
real = open(RTE, 'rb').read() if os.path.exists(RTE) else b'x' * 9000
bad = 0
for n, data in (('zeros', bytes(8192)), ('text', b'not a revit file' * 300), ('trunc', real[:len(real) // 2])):
    for how in ('saveas', 'overwrite'):
        src = tempfile.mkdtemp(dir=_T) + '/s.rvt'; open(src, 'wb').write(data); dest = src + '.out'; h0 = sha(src)
        try:
            ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
            save.add_edit(ss, 'm', src, {'op': 'move', 'eid': 24, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0})
            save.save_as(ss, 'm', src, dest) if how == 'saveas' else save.save_overwrite(ss, 'm', src)
            print('FAIL accepted', n, how); bad += 1
        except Exception as e: print('refused', n, how, type(e).__name__, str(e)[:70].replace('\n', ' '))
        if sha(src) != h0 or os.path.exists(dest): print('FAIL source/target changed', n, how); bad += 1
sys.exit(1 if bad else 0)
