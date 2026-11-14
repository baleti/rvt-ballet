"""Revit 2024 paired run (HVAC sample, fitting move +1 ft): Revit regenerated 24 connected duct/fitting records. A move of an element that has connector refs (m_pConnectorManager.m_arrRefs) must be flagged risky so the in-place save refuses it. Needs the Autodesk HVAC 2024 base kept local by the diff lab; skipped when absent."""
import os, pytest
BASE = os.path.expanduser('~/c2x-diff/mvtag24/base.rvt')
pytestmark = pytest.mark.skipif(not os.path.exists(BASE), reason='HVAC 2024 base not present')

def test_connected_fitting_move_is_risky():
    from rvtballet.save import membership, risky_membership
    buf = open(BASE, 'rb').read()
    ids = [1409785, 1407319]
    ops = [{'op': 'move', 'eid': i} for i in ids]
    r = risky_membership(membership(buf, set(ids)), ops)
    for i in ids: assert any(x.startswith('connected to ') for x in r.get(i, [])), r
    # a parameter edit of the same fitting is not a move: not flagged for connectivity
    assert 1409785 not in risky_membership(membership(buf, {1409785}), [{'op': 'set_str', 'eid': 1409785}])


STRUCT = os.path.expanduser('~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt')

@pytest.mark.skipif(not os.path.exists(STRUCT), reason='Structural 2024 sample not present')
def test_geometry_joined_instance_move_is_risky():
    """607834 is geometry-joined (m_geomJoined) to 6 instances and was unflagged before this guard."""
    from rvtballet.save import membership, risky_membership
    buf = open(STRUCT, 'rb').read()
    r = risky_membership(membership(buf, {607834, 606905}), [{'op': 'move', 'eid': 607834}, {'op': 'move', 'eid': 606905}])
    for i in (607834, 606905): assert any(x.startswith('joined to ') for x in r.get(i, [])), r


@pytest.mark.skipif(not os.path.exists(STRUCT), reason='Structural 2024 sample not present')
def test_framing_support_move_is_risky():
    """608203 is a point-located column named by 10 beams' m_endStructId and was accepted before."""
    from rvtballet.save import membership, risky_membership
    buf = open(STRUCT, 'rb').read()
    r = risky_membership(membership(buf, {608203}), [{'op': 'move', 'eid': 608203}])
    assert any(x.startswith('supports ') for x in r.get(608203, [])), r


@pytest.mark.parametrize('y,f', [(2025, '48_Snowdon_Towers_Sample_HVAC.rvt'), (2026, '54_Snowdon_Towers_Sample_HVAC.rvt')])
def test_connected_fitting_move_is_risky_2025_2026(y, f):
    p = os.path.expanduser('~/rvt-research/corpus/%d/%s' % (y, f))
    if not os.path.exists(p): pytest.skip('sample not present')
    from rvtballet.save import membership, risky_membership
    ids = [1409785, 1407319]
    r = risky_membership(membership(open(p, 'rb').read(), set(ids)), [{'op': 'move', 'eid': i} for i in ids])
    for i in ids: assert any(x.startswith('connected to ') for x in r.get(i, [])), r
