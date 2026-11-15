"""c3x-rvtdel: production delete gate on Revit 2020-2023 files (no DELETE_ANY): a FamilyInstance/SWall delete must be refused with the year message (verified: 2024; 2026 subset), source untouched."""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ.update(SAVEGATE_JOURNAL=_T+'/j', SAVEGATE_CACHE=_T+'/c', RVTBALLET_SNAPSHOT_CACHE=_T+'/snap', RVTBALLET_EDIT_BACKEND='rvtedit', RVTBALLET_ENABLE_DELETE='1')
os.environ.pop('RVTBALLET_DELETE_ANY', None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab')): sys.path.insert(0, p)
from rvtballet import save, edit
import rvt_params
FILES = {2022: '30_rst_basic_sample_project.rvt', 2023: None}
if not save.SaveSessions().available: print('skip'); sys.exit(0)
try:
    n = 0
    for y in (2020, 2021, 2022, 2023):
        dd = os.path.expanduser('~/rvt-research/corpus/%d' % y)
        fs = sorted(f for f in os.listdir(dd) if f.endswith('.rvt') and not f.endswith('.tsv')) if os.path.isdir(dd) else []
        if not fs: print('no file', y); continue
        src = os.path.join(_T, 's%d.rvt' % y); shutil.copy(os.path.join(dd, fs[0]), src); h0 = hashlib.sha256(open(src, 'rb').read()).hexdigest()
        try: d = save.SaveSessions().doc('m%d' % y, src)
        except Exception as e:      # earliest refusal: the save session itself only opens writable years (2024-2026)
            assert 'cannot be saved' in str(e) and 'writable years' in str(e), (y, str(e)[:200]); n += 1
            assert hashlib.sha256(open(src, 'rb').read()).hexdigest() == h0; continue
        pr = rvt_params.params(src)
        for c in ('FamilyInstance', 'SWall'):
            ids = [e for e, v in pr.items() if isinstance(v, dict) and v.get('class') == c][:1]
            if not ids: continue
            try: edit.apply_full(d.buf, [edit.validate_op({'op': 'delete', 'eid': ids[0]})]); msg = ''
            except edit.EditError as e: msg = str(e)
            assert 'not VM-verified on Revit %d' % y in msg, (y, c, msg[:200]); n += 1
        assert hashlib.sha256(open(src, 'rb').read()).hexdigest() == h0
    print('OK year-gate refusals', n)
finally: shutil.rmtree(_T, ignore_errors=True)
