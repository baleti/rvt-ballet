"""regression (c4x-rvtmatrix): set_string IfcGUID on duct 1379374 of the public 2024 Snowdon HVAC sample is shown by the reader on its SegmentCenterLine 1379375 under 'IfcGUID' AND 'Type IfcGUID'; derived_echoes must declare it (strict old->new on exactly those keys), otherwise the gate refuses an honest save. Also: a dependent that changed some OTHER key is not declared."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
from rvtballet import edit, save
D = os.path.expanduser('~/rvtfix/corpus/2024/42_Snowdon_Towers_Sample_HVAC.rvt')
if not os.path.exists(D) or not save._import(): print('skip'); sys.exit(0)
db = open(D, 'rb').read(); o = edit.validate_op({'op': 'set_string', 'eid': 1379374, 'param': 'IfcGUID', 'value': 'zzTEST'}); nd, _ = edit.apply_full(db, [o])
e = save.derived_echoes(db, nd, [o])
if e != [1379375]: print('FAIL echoes', e); sys.exit(1)
print('derived echo declared:', e)
a, b = save._read_params(db), save._read_params(nd)
b2 = dict(b); x = dict(b[1379375]); x2 = x.get('params', x); x2 = dict(x2); x2['Flow'] = 99.0; b2[1379375] = {'params': x2} if 'params' in x else x2
save._RB_MEMO.insert(0, (__import__('hashlib').sha256(b'fake').digest(), b2))
e2 = save.derived_echoes(db, b'fake', [o])
if 1379375 in e2: print('FAIL undeclared extra change accepted'); sys.exit(1)
print('extra changed key not declared OK')
