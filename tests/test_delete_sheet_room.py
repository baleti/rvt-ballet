"""Delete regression (rung 2, c1x-rvtdel item 108/99): sheet DBDrawing 251 and room RoomElem 583143 of Structural 2024 deletes cleanly: id removed, survivors identical. Room needs the savegate part_header delete rule (0610c4d)."""
import os, sys, tempfile, shutil
os.environ['RVTBALLET_ENABLE_DELETE'] = '1'; os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
import atexit as _ax, shutil as _sh; _T = tempfile.mkdtemp(); _ax.register(_sh.rmtree, _T, True); os.environ['SAVEGATE_JOURNAL'] = _T + '/j'; os.environ['SAVEGATE_CACHE'] = _T + '/c'; os.environ['RVTBALLET_SNAPSHOT_CACHE'] = _T + '/snap'; os.environ['RVTBALLET_EDIT_BACKUPS'] = _T + '/b'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
for p in (os.path.expanduser('~/rvt-research'), os.path.expanduser('~/rvt-research/write-lab'), os.path.expanduser('~/src/savegate')): sys.path.insert(0, p)
SRC = os.path.expanduser('~/c2x-tmp/ip25/2024_43_Snowdon_Towers_Sample_Structural.rvt')
from rvtballet import save, edit
import rvt_params
if not os.path.exists(SRC) or not save.SaveSessions().available: print('skip'); sys.exit(0)
src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src)
pr = rvt_params.params(src)

src = os.path.join(_T, 'src.rvt'); shutil.copy(SRC, src)
pr = rvt_params.params(src)
d0 = save.SaveSessions().doc('msheet', src)
for eid, cls in ((251, 'DBDrawing'), (583143, 'RoomElem')):      # room: VM-verified class; gate needs the part_header delete rule
    assert pr[eid].get('class') == cls, (eid, pr[eid].get('class'))
    d = save.SaveSessions().doc('m' + str(eid), src)
    ops = [edit.validate_op({'op': 'delete', 'eid': eid})]
    nb, deleted = edit.apply_full(d.buf, ops); assert eid in deleted
    save._readback(d.buf, nb, ops)
    out = os.path.join(_T, 'out%d.rvt' % eid); open(out, 'wb').write(nb)
    p2 = rvt_params.params(out)
    assert eid not in p2 and set(p2) == set(pr) - set(deleted), (eid, len(p2), len(pr), len(deleted))
    assert all(p2[e] == pr[e] for e in p2 if e not in deleted), 'survivor drift'
    print(cls, eid, 'delete OK', len(deleted), flush=True)
