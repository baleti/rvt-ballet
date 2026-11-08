"""Corruption AFTER the in-memory verification (c7x-rvtmatrix): the savegate temp-file writer is wrapped so the bytes that reach the disk differ from the verified result
(flip middle byte, flip tail byte, truncate 1, 4 KB of zeros). SAVE AS and SAVE! with a real edit and with identity. Invariant: every case refused, source bytes untouched,
SAVE AS target absent. Without the read-back check in savegate this would be accepted (the wrapper sanity case with no corruption must succeed)."""
import atexit, shutil as _sh, tempfile as _tf
_made = []
_mkd0 = _tf.mkdtemp
def _mkd(*a, **k):
    d = _mkd0(*a, **k); _made.append(d); return d
_tf.mkdtemp = _mkd; atexit.register(lambda: [_sh.rmtree(d, ignore_errors=True) for d in _made])
import os, sys, tempfile, shutil, hashlib
_T = tempfile.mkdtemp(dir=os.environ.get('TMPDIR')); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def main():
    from rvtballet import save
    save._import()
    import savegate as sg, savegate.atomic as A
    orig = A.write_temp; mode = [None]
    def bad(dest, data):
        b = bytearray(data); m = mode[0]
        if m == 'flip_mid': b[len(b) // 2] ^= 0x10
        elif m == 'flip_tail': b[-50] ^= 0x01
        elif m == 'trunc1': b = b[:-1]
        elif m == 'zero4k': i = len(b) // 3; b[i:i + 4096] = b'\x00' * 4096
        return orig(dest, bytes(b))
    A.write_temp = bad; esc = tot = 0
    for kind in ('identity', 'edit'):
        for how in ('saveas', 'overwrite'):
            for md in (None, 'flip_mid', 'flip_tail', 'trunc1', 'zero4k'):
                d = tempfile.mkdtemp(dir=_T); src = d + '/s.rvt'; dest = d + '/o.rvt'; shutil.copy(RTE, src); h0 = sha(src); mode[0] = None
                ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src)
                if kind == 'edit': save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': 24, 'value': 'Edited by test', 'match': ''})
                mode[0] = md; tot += 1
                try:
                    save.save_as(ss, 'm', src, dest) if how == 'saveas' else save.save_overwrite(ss, 'm', src); res = 'ACCEPTED'
                except Exception as e:
                    res = 'refused ' + type(e).__name__
                    if md is not None and type(e).__name__ != 'DiskError': res += ' (WRONG REASON)'
                mode[0] = None; ss.close()
                bad_ok = (md is None) == (res == 'ACCEPTED') and 'WRONG' not in res       # no corruption must pass, corruption must be refused
                intact = how == 'overwrite' and kind == 'identity' and md is not None and sha(src) == h0 or how == 'saveas' and sha(src) == h0 or md is None or kind == 'edit' and sha(src) == h0
                if how == 'saveas' and md is not None and os.path.exists(dest): intact = False
                if not bad_ok or not intact: esc += 1
                print(kind, how, md, res, 'OK' if bad_ok and intact else 'FAIL')
    print('cases', tot, 'failures', esc); assert esc == 0
if __name__ == '__main__': main()
