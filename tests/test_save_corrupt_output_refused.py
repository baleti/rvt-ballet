"""ESCAPE guard (RVT in place): if the writer output has a flipped byte (middle / body) or a zeroed tail, the gate must refuse and the source stays byte-identical."""
import os, sys, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['SAVEGATE_BACKUPS'] = _T + '/bk'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save
save._import(); import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def session(src):
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); ss.doc('m', src); return ss
def main():
    if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip'); return
    wd = tempfile.mkdtemp(dir=os.path.expanduser('~')); src = wd + '/s.rvt'; alt = wd + '/alt.rvt'; shutil.copy(RTE, src); shutil.copy(RTE, alt); h = sha(src)
    try:
        ss = session(src); save.add_edit(ss, 'm', src, {'op': 'set_string', 'eid': 24, 'value': 'asked', 'match': ''})
        import rvtballet.edit as E
        real = E.apply_full
        def mk(mode):
            def f(buf, ops):
                out, x = real(buf, ops); o = bytearray(out)
                if mode == "mid": o[len(o) // 2] ^= 0xFF
                elif mode == "body": o[len(o) * 3 // 4] ^= 0x01
                else: o[-4096:] = bytes(4096)
                return bytes(o), x
            return f
        for mode in ("mid", "body", "tail"):
            E.apply_full = mk(mode); refused = None
            try: save.save_overwrite(ss, "m", src)
            except Exception as e: refused = "%s: %s" % (type(e).__name__, str(e)[:100])
            finally: E.apply_full = real
            print(mode, "->", refused)
            assert refused, "ESCAPE: corrupted writer output (%s) was written" % mode
            assert sha(src) == h, "source changed"
        ss.close(); print("corrupt output refused OK")
    finally: shutil.rmtree(wd, True)
main()
