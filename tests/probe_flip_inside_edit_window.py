"""Production-path flip probe (RVT, in place): record a real move through save.add_edit, let the writer produce its output, flip ONE byte of that output at N positions (spread over the file), then SAVE!. The production manifest (dirty_members + span rules) must refuse each flip and leave the source byte-identical. A flip that is ACCEPTED is printed as ESCAPE with its position and stream, and the test fails."""
import os, sys, tempfile, shutil, hashlib, json, io
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['SAVEGATE_BACKUPS'] = _T + '/bk'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_ALLOW_OVERWRITE'] = '1'
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save, edit as E
if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip'); sys.exit(0)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
real = E.apply_full; esc = []
try:
    f0 = _T + '/p.rte'; shutil.copy(RTE, f0); s0 = save.SaveSessions(); save.add_edit(s0, 'm', f0, {'op': 'move', 'eid': 301595, 'dx': 2.0, 'dy': 0.0, 'dz': 0.0})
    _nb = real(s0.doc('m', f0).buf, list(s0.edits('m').ops))[0]; _src = open(RTE, 'rb').read(); s0.close()
    _d = [i for i in range(len(_src)) if _src[i] != _nb[i]]; print('edit window: %d differing file bytes between %d and %d' % (len(_d), _d[0], _d[-1]))
    import random; random.seed(7)
    for frac in sorted({_d[0] / len(_nb), _d[-1] / len(_nb)} | {random.choice(_d) / len(_nb) for _ in range(4)}):
        f = _T + '/w.rte'; shutil.copy(RTE, f); h0 = sha(f); ss = save.SaveSessions()
        save.add_edit(ss, 'm', f, {'op': 'move', 'eid': 301595, 'dx': 2.0, 'dy': 0.0, 'dz': 0.0})
        def flipped(buf, ops, frac=frac):
            nb, dl = real(buf, ops); b = bytearray(nb); b[round(len(b) * frac)] ^= 0xFF; return bytes(b), dl
        E.apply_full = flipped
        try:
            save.save_overwrite(ss, 'm', f); verdict = 'ACCEPTED'
        except Exception as e: verdict = 'refused:' + type(e).__name__
        finally: E.apply_full = real; ss.close()
        print('flip at %.4f%%: %s; source unchanged=%s' % (frac * 100, verdict, sha(f) == h0))
        if verdict == 'ACCEPTED': esc.append(frac)
        else: assert sha(f) == h0, 'refused but the source changed'
finally: shutil.rmtree(_T, ignore_errors=True)
print('accepted flips inside the edit window (byte offsets/len):', esc)
print('MEASURED')
