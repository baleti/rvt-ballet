"""Snowdon Structural 2024: a curve-located beam (FamInstCurveDriver) is refused at the EDIT stage with a clear message; the column next to it (point-located) is still accepted. Local corpus only; skips if absent."""
import os, sys, tempfile, shutil
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SRC = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')
from rvtballet import edit
def main():
    if not os.path.exists(SRC): print('skip'); return
    wd = tempfile.mkdtemp(); dst = wd + '/o.rvt'
    try:
        for eid, want_ok in ((606873, False), (606069, True)):
            try: edit.apply(open(SRC,'rb').read(), [edit.validate_op({'op': 'move', 'eid': eid, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0})]); ok = True; msg = ''
            except edit.EditError as e: ok = False; msg = str(e)
            print(eid, 'accepted' if ok else 'refused', msg[:90])
            assert ok == want_ok, (eid, msg)
            if not want_ok: assert 'curve-located' in msg
    finally: shutil.rmtree(wd, True)
    print('OK')
main()
