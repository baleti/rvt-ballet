"""c3x-rvttype: set_type_material on the Autodesk 2026 Structural sample (SysMullionFamSym 378, Material 1075 -> 751): same material, missing target, non-material target, bad eid, non-positive target are refused with nothing produced; the control applies. Skips if the sample is absent."""
import os, sys, glob
sys.path[:0] = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'), os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/rvt-research/edit-lab')]
os.environ.update(RVT_GEOM='1', RVTBALLET_ENABLE_TYPEEID='1', RVTBALLET_EDIT_BACKEND='rvtedit')
fs = glob.glob(os.path.expanduser('~/rvt-research/corpus/2026/55_*Structural*.rvt'))
if not fs: print('skip'); sys.exit(0)
from rvtballet import edit
buf = open(fs[0], 'rb').read(); bad = 0
B = {'op': 'set_type_material', 'eid': 378, 'target': 751}
for n, o in {'same': dict(B, target=1075), 'missing': dict(B, target=999999999), 'not_material': dict(B, target=378), 'bad_eid': dict(B, eid=999999999), 'zero_target': dict(B, target=0)}.items():
    try: edit.apply_full(buf, [edit.validate_op(o)]); print('FAIL accepted', n); bad += 1
    except edit.EditError as e: print('refused', n, '|', str(e)[:70])
    except Exception as e: print('FAIL non-EditError', n, type(e).__name__, str(e)[:60]); bad += 1
try: out, _ = edit.apply_full(buf, [edit.validate_op(B)]); print('control ok', len(out))
except Exception as e: print('FAIL control', e); bad += 1
sys.exit(1 if bad else 0)
