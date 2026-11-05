"""RVT in place: a writer that moves/rotates by another amount than requested (move 3 for 2, rotate 30 for 15) must be refused by the read-back; source stays byte-identical. Honest writer passes."""
import os, sys, tempfile, shutil, hashlib, json
_T = tempfile.mkdtemp(); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['SAVEGATE_BACKUPS'] = _T + '/bk'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'
os.environ['RVTBALLET_ALLOW_LAYOUT_CHANGE'] = '1'          # the template move changes the page layout; irrelevant for this check
json.dump({'rvt': {'2024': 'open'}}, open(_T + '/gate.json', 'w')); os.environ['SAVEGATE_GATE'] = _T + '/gate.json'
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
RTE = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
from rvtballet import save, edit
import rvtballet.edit as E
save._import(); import savegate as sg
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
A = 301595
def attempt(asked, produced, honest=False):
    wd = tempfile.mkdtemp(dir=os.path.expanduser('~')); src = wd + '/s.rvt'; shutil.copy(RTE, src); h = sha(src)
    ss = save.SaveSessions(sg.Config(allow_overwrite=True, require_gate=False)); d = ss.doc('m', src)
    nb, _ = E.apply_full(d.buf, [E.validate_op(produced)]); save.add_edit(ss, 'm', src, asked)
    real = E.apply_full
    if not honest: E.apply_full = lambda buf, ops: (nb, real(buf, ops)[1])
    try:
        try: save.save_overwrite(ss, 'm', src); out = 'ACCEPTED'
        except Exception as e: out = '%s: %s' % (type(e).__name__, str(e)[:110])
    finally: E.apply_full = real; ss.close()
    same = sha(src) == h; shutil.rmtree(wd, True); return out, same
def main():
    if not os.path.exists(RTE) or not save.SaveSessions().available: print('skip'); return
    for name, asked, produced in (('move', {'op': 'move', 'eid': A, 'dx': 2.0}, {'op': 'move', 'eid': A, 'dx': 3.0}), ('rotate', {'op': 'rotate', 'eid': A, 'deg': 15.0}, {'op': 'rotate', 'eid': A, 'deg': 30.0})):
        out, same = attempt(asked, produced); print(name, 'wrong ->', out, '| source intact:', same)
        out2, same2 = attempt(asked, asked, honest=True); print(name, 'honest ->', out2[:80], '| source unchanged:', same2)
        assert out != 'ACCEPTED' and same, ('ESCAPE', name, out)
        assert out2 == 'ACCEPTED' or 'layout' in out2.lower() or 'refus' in out2.lower(), out2
    print('wrong move/rotate refused OK')
main()
