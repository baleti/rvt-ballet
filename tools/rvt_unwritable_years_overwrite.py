#!/usr/bin/env python3
"""rvt_unwritable_years_overwrite.py CORPUS_ROOT [YEARS...]: for each year dir, the smallest .rvt/.rfa/.rte is copied into a private dir and an in-place SAVE! is attempted with overwrite ON but the REAL default gate (only
the verified years are writable). Pass = writable years may save, every other year is REFUSED, the copy is byte-identical afterwards and the directory holds no extra file (no backup/tmp debris). Aggregate rows only (year, size, outcome)."""
import os, sys, shutil, tempfile, hashlib
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'; t = tempfile.mkdtemp(prefix='uwy-'); os.environ['SAVEGATE_JOURNAL'] = t + '/j'; os.environ['SAVEGATE_CACHE'] = t + '/c'
from rvtballet import save
root = sys.argv[1]; years = sys.argv[2:] or sorted(os.listdir(root)); bad = 0
for y in years:
    fs = [os.path.join(root, y, f) for f in os.listdir(os.path.join(root, y)) if f.lower().endswith(tuple(os.environ.get('EXTS', '.rvt .rfa .rte').split()))]
    if not fs: continue
    f = min(fs, key=os.path.getsize); d = tempfile.mkdtemp(prefix='uwd-', dir=t); p = os.path.join(d, 'a' + os.path.splitext(f)[1]); shutil.copy(f, p)
    h0 = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    try: save.save_overwrite(save.SaveSessions(), 'm1', p); out = 'SAVED'
    except Exception as e: out = 'REFUSED(%s)' % type(e).__name__
    same = hashlib.sha256(open(p, 'rb').read()).hexdigest() == h0; extra = sorted(os.listdir(d)); clean = extra == [os.path.basename(p)]
    ok = (out != 'SAVED' or y in ('2024', '2026')) and (same or out == 'SAVED') and (clean or out == 'SAVED')
    bad += not ok; print(y, round(os.path.getsize(p) / 2 ** 20, 1), 'MB', out, 'identical' if same else 'CHANGED', 'clean-dir' if clean else 'DEBRIS %d' % len(extra), 'OK' if ok else 'BAD', flush=True)
shutil.rmtree(t, True); sys.exit(1 if bad else 0)
