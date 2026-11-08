"""c1x-rvtsave 182: one-byte flips in CFB header bytes that are zero/fixed in every Revit-made file (CLSID 8..23, num dir sectors 40, num mini FAT sectors 64, byte order 28..29, reserved 34..39, transaction signature 52..55) must be refused by an in-place save, source untouched; an unflipped file still saves."""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import()
import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
try:
    raw = open(RTE, 'rb').read(); sd = save.source_damage
    assert sd(raw) == [], sd(raw)
    for o in (8, 15, 23, 28, 29, 34, 39, 52, 55, 40, 41, 64, 65):
        b = bytearray(raw); b[o] ^= 0x40; assert sd(bytes(b)), 'offset %d flip not flagged' % o
    for o in (8, 28, 52):      # through the real in-place path
        b = bytearray(raw); b[o] ^= 0x40; src = os.path.join(_T, 'x.rvt'); open(src, 'wb').write(bytes(b)); h = sha(src)
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
        try: save.save_overwrite(ss, 'm', src); raise SystemExit('FAIL offset %d accepted' % o)
        except SystemExit: raise
        except Exception as e: print(o, 'refused', type(e).__name__)
        assert sha(src) == h
    print('OK')
finally: shutil.rmtree(_T, ignore_errors=True)
