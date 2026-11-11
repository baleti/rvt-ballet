"""c4x-rvtwrite2 182b: SAVE AS and in-place SAVE! of a set_num 'Unconnected Height' edit (synthetic 2024 cols2 scene, wall 301553) both return the no-op warning in the result JSON."""
import os, sys, shutil, tempfile, json
T = tempfile.mkdtemp()
json.dump({'allow_overwrite': True}, open(T + '/c.json', 'w')); json.dump({'rvt': {'*': 'open'}}, open(T + '/g.json', 'w'))
os.environ.update(SAVEGATE_JOURNAL=T + '/j', SAVEGATE_CACHE=T + '/c', DWG_BALLET_CONFIG=T + '/c.json', SAVEGATE_GATE=T + '/g.json', RVTBALLET_ALLOW_OVERWRITE='1', RVTBALLET_EDIT_BACKEND='rvtedit')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pytest
from rvtballet import save
S = os.path.expanduser('~/rvt-research/write-lab/scenes/classtests/2024_writer_cols2.rte')
OP = {'op': 'set_num', 'eid': 301553, 'param': 'Unconnected Height', 'value': 11.0, 'kind': 'Double'}

def _run(inplace):
    if not os.path.exists(S) or not save.SaveSessions().available: pytest.skip('scene or savegate missing')
    p = T + '/m%d.rvt' % inplace; shutil.copy(S, p); ss = save.SaveSessions(); ss.doc('m', p)
    save.add_edit(ss, 'm', p, dict(OP))
    r = save.save_overwrite(ss, 'm', p) if inplace else save.save_as(ss, 'm', p, T + '/out.rvt')
    return r.get('warnings') or [] if isinstance(r, dict) else []

@pytest.mark.parametrize('inplace', [False, True])
def test_warning_in_result(inplace):
    w = _run(inplace)
    assert any('Unconnected Height' in x and 'Top Offset' in x for x in w), w
