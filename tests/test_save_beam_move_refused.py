"""rst_basic 2023 framing beam 1046268, SAVE AS +1 ft: the writer moves the record origin but the beam box is geometry-derived, so the element-level verify must REFUSE (verify_failed), write nothing, and leave the source byte-identical. Pins queue item 17 (c1x-rvtmove): no corrupted/semantically wrong beam move is accepted. Production gate: a 2023 file is refused at sniff (UnsupportedVersion); the element-level refusal was seen only under the experimental all-years gate. Fast."""
import os, sys, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['SAVEGATE_BACKUPS'] = _T + '/bk'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
json.dump({'rvt': {'2023': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
SRC = os.path.expanduser('~/rvt-research/corpus/2023/36_rst_basic_sample_project.rvt'); BEAM = 1046268
from rvtballet import save, edit
save._import(); import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
def main():
    if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); return
    wd = tempfile.mkdtemp(dir=os.path.expanduser('~')); src = wd + '/s.rvt'; dst = wd + '/o.rvt'; shutil.copy(SRC, src); h = sha(src)
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False))
    try:
        try: save.add_edit(ss, 'm', src, {'op': 'move', 'eid': BEAM, 'dx': 1.0, 'dy': 0.0, 'dz': 0.0}); save.save_as(ss, 'm', src, dst); out = 'ACCEPTED'
        except Exception as e: out = '%s: %s' % (type(e).__name__, str(e)[:160])
    finally: ss.close()
    print('beam move ->', out, '| output exists:', os.path.exists(dst), '| source intact:', sha(src) == h)
    ok = sha(src) == h and (out != 'ACCEPTED' or True)
    assert sha(src) == h, 'source damaged'
    assert out != 'ACCEPTED' and not os.path.exists(dst), ('ESCAPE', out)
    if out == 'ACCEPTED': print('NOTE: accepted; then the output must have been verified element-level (shift (1,0,0))')
    shutil.rmtree(wd, True); print('OK')
main()
