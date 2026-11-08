"""In-place save after the source was changed on disk by someone else (after load): must be refused, the external version stays byte-identical, no temp left."""
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save

save._import()
import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def main():
    try:
        src = os.path.join(_T, 'src.rvt'); shutil.copy(RTE, src)
        ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
        for kind in ('append', 'same_size_flip'):
            b = bytearray(open(src, 'rb').read())
            if kind == 'append': b += b'\0' * 512
            else: b[-1] ^= 0xFF
            open(src, 'wb').write(bytes(b)); h = sha(src)
            try: save.save_overwrite(ss, 'm', src); raise SystemExit('FAIL %s: save accepted over an external change' % kind)
            except SystemExit: raise
            except Exception as e: print(kind, 'refused:', type(e).__name__, str(e)[:120])
            assert sha(src) == h, kind + ': external version damaged'
            assert not [f for f in os.listdir(_T) if 'sgtmp' in f or f.endswith('.part')], 'leftover'
            shutil.copy(RTE, src); ss.close(); ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False, verify=False)); ss.doc('m', src)
        print('OK')
    finally: shutil.rmtree(_T, ignore_errors=True)
main()
