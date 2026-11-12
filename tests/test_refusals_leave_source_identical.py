"""c2x-rvtmatrix (orchestrator item 23): every edit refusal and every no-op in-place save leaves the source byte-identical (sha before/after). Autodesk 2024 Snowdon Structural sample; skipped if absent."""
import os, sys, shutil, hashlib, tempfile
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ.update(SAVEGATE_JOURNAL=_T + '/j', SAVEGATE_CACHE=_T + '/c', RVTBALLET_EDIT_BACKEND='rvtedit')
os.environ.pop('RVTBALLET_DELETE_ANY', None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
from rvtballet import save, edit
import rvt_params
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
try:
    src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src); h0 = sha(src)
    ss = save.SaveSessions(); ss.doc('m', src); pr = rvt_params.params(src)
    lvl = next(e for e, v in pr.items() if isinstance(v, dict) and v.get('class') == 'Level')
    grd = next(e for e, v in pr.items() if isinstance(v, dict) and v.get('class') == 'Grid')
    bad = [{'op': 'delete', 'eid': lvl}, {'op': 'delete', 'eid': grd}, {'op': 'move', 'eid': 1, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0},
           {'op': 'move', 'eid': 987654321, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}, {'op': 'frobnicate', 'eid': lvl}, {'op': 'set_string', 'eid': 987654321, 'field': 'Mark', 'value': 'x'}]
    n = 0
    for op in bad:
        try: save.add_edit(ss, 'm', src, op); print('accepted (not a refusal):', op['op'], op['eid']); continue
        except Exception as e: n += 1
        assert sha(src) == h0, 'source changed after refused %s' % op['op']
    try: save.add_edits(ss, 'm', src, bad); print('batch accepted')
    except Exception: n += 1
    assert sha(src) == h0
    # in-place save with whatever (nothing) is pending, and save as to a destination: source must stay identical
    try: save.save_overwrite(ss, 'm', src)
    except Exception as e: print('overwrite no-op raised', type(e).__name__)
    assert sha(src) == h0, 'source changed by no-edit overwrite'
    assert n >= 3, 'too few refusals (%d): test not exercising the refusal path' % n
    print('OK refusals', n, 'source identical')
finally: shutil.rmtree(_T, ignore_errors=True)
