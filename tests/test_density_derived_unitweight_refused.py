"""Editing Density of a material asset changes the reader-derived Unit weight; the
readback gate must refuse (VerifyFailed) and leave the file untouched. Safe direction
until a Revit VM verdict justifies a derived-parameter allowance. Skips without the scene."""
import os, sys, shutil, tempfile, hashlib
SRC = os.path.expanduser('~/rvt-research/write-lab/files/e1_level_2026.rte')
if not os.path.exists(SRC): print('SKIP: scene missing'); sys.exit(0)
T = tempfile.mkdtemp()
open(T+'/c.json','w').write('{"allow_overwrite": true}'); open(T+'/g.json','w').write('{"rvt": {"*": "open"}}')
os.environ.update(SAVEGATE_JOURNAL=T+'/j', SAVEGATE_CACHE=T+'/c', DWG_BALLET_CONFIG=T+'/c.json', SAVEGATE_GATE=T+'/g.json', RVTBALLET_ALLOW_OVERWRITE='1', RVTBALLET_EDIT_BACKEND='rvtedit')
sys.path[:0] = [os.path.expanduser('~/src/rvt-viewer'), os.path.expanduser('~/src/savegate'), os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]
from rvtballet import save
p = T+'/m.rvt'; shutil.copy(SRC, p); h = hashlib.sha256(open(p,'rb').read()).hexdigest()
ss = save.SaveSessions(); ss.doc('m', p)
save.add_edit(ss, 'm', p, {"op": "set_num", "eid": 138783, "param": "Density", "value": 8.7118855})
try: save.save_overwrite(ss, 'm', p); raise SystemExit('FAIL: Density edit was saved')
except SystemExit: raise
except Exception as ex: assert 'VerifyFailed' in type(ex).__name__ or 'other parameter' in str(ex), repr(ex)
assert hashlib.sha256(open(p,'rb').read()).hexdigest() == h, 'original changed'
print('density edit refused, file untouched OK')
