"""fastquery speedups of 2026-11-17 (switches RVT_Q_SLIM / SYMSTOP / INLINE / EARLYCAT / R2SKIP / FASTFAT / ESFORK): (1) synthetic, no .rvt bytes:
_inline_safe on a small schema, the forked ES-schema child (result, failure and timeout fall back to None), linear FAT load == olefile's; (2) Autodesk
samples (skipped when the corpus is absent): collect / sheets output identical with every switch on vs off. Run: python -m pytest tests/test_fastquery_speed.py"""
import os, sys, time, json
import pytest
HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'); sys.path.insert(0, HERE)
from rvtballet import fastquery as Q

CORPUS = os.path.expanduser('~/rvt-research/corpus')
SAMPLES = ['2018/09_rac_advanced_sample_project.rvt', '2020/19_Commercial_Sample_Project.rvt', '2021/27_Technical_school-current_m.rvt',
           '2024/42_Snowdon_Towers_Sample_HVAC.rvt', '2026/55_Snowdon_Towers_Sample_Structural.rvt']
SWITCHES = ('SLIM', 'SYMSTOP', 'INLINE', 'EARLYCAT', 'R2SKIP', 'FASTFAT', 'ESFORK')

# kind 0x0e = struct/pointer; flags byte: 1-3 pointer slot, 0x5x set/vector of pointers, 0 embedded struct (ref = class tag); kind 0x05 = a primitive
PTR, EMB, PRIM = 0x010e, 0x000e, 0x0005


def schema():
    c = lambda name, fields, parent=None: {'name': name, 'fields': fields, 'parent': parent}
    return [c('ElementId', [{'name': 'm_id', 'types': [PRIM]}]),                                          # tag 12
            c('Element', [{'name': 'm_assocLevelId', 'types': [EMB], 'ref': 12}, {'name': 'm_pGeom', 'types': [PTR]}]),   # 13
            c('Plain', [{'name': 'm_text', 'types': [PRIM]}], 13),                                         # 14
            c('ByPtr', [{'name': 'm_pMaterial', 'types': [PTR]}], 13),                                     # 15
            c('Holder', [{'name': 'm_x', 'types': [PTR]}]),                                                # 16: has a pointer
            c('ByEmb', [{'name': 'm_name', 'types': [EMB], 'ref': 16}], 13),                               # 17: name in an embedded struct holding a pointer
            c('PtrSet', [{'name': 'm_typeId', 'types': [0x510e]}], 13)]                                    # 18: set of pointers


def test_inline_safe_synthetic():
    cls = schema(); kp = frozenset(('name', 'm_assocLevelId', 'm_typeId'))
    assert Q._inline_safe(cls, 2, kp)            # m_text primitive, inherited level id an embedded ElementId (no pointer); m_pGeom is not read
    assert not Q._inline_safe(cls, 3, kp)        # name source behind a pointer (MaterialElem.m_pMaterial)
    assert not Q._inline_safe(cls, 5, kp)        # embedded struct that holds a pointer
    assert not Q._inline_safe(cls, 6, kp)        # set of pointers
    assert Q._inline_safe(cls, 1, kp)


class _O:
    def __init__(self, data): self.data = data
    def openstream(self, name):
        import io; return io.BytesIO(self.data)


class _Fmt:
    @staticmethod
    def inflate_stream(b): return (None, b, None)


class _F:
    def __init__(self, fn): self.find_schemas = fn


def test_es_child_result_failure_and_timeout(monkeypatch):
    ok = Q._es_start(_O(b'abc'), None, 8, _Fmt, _F(lambda d, sch, W: {'n': len(d), 'W': W}))
    assert Q._es_join(ok) == {'n': 3, 'W': 8}
    def boom(d, sch, W): raise RuntimeError('x')
    assert Q._es_join(Q._es_start(_O(b'abc'), None, 8, _Fmt, _F(boom))) is None
    monkeypatch.setattr(Q, 'ES_TIMEOUT', 0.3)
    t = time.time(); stuck = Q._es_start(_O(b'abc'), None, 8, _Fmt, _F(lambda d, sch, W: time.sleep(30)))
    assert Q._es_join(stuck) is None and time.time() - t < 5          # killed after the timeout, caller computes in process
    assert Q._es_join(None) is None


def _samples():
    ps = [os.path.join(CORPUS, s) for s in SAMPLES if os.path.exists(os.path.join(CORPUS, s))]
    if not ps: pytest.skip('Autodesk corpus absent')
    return ps


def test_fast_fat_equals_olefile():
    import olefile
    for p in _samples():
        assert list(olefile.OleFileIO(p).fat) == list(Q._ole_class(olefile)(p).fat), p


def _set(monkeypatch, on):
    for k in SWITCHES: monkeypatch.setattr(Q, k, on)


@pytest.mark.parametrize('kw', [{'cls': 'Wall'}, {'cls': 'Level'}, {'cls': 'WallType'}, {'cls': 'FamilySymbol'}, {'cls': 'Material'}, {'cls': 'View'},
                                {'category': 'Doors'}, {'category': 'Windows'}, {'cls': 'FamilyInstance'}, {'cls': 'Dimension'}, {'cls': 'Room'}],
                         ids=lambda k: '-'.join(map(str, k.values())))
def test_collect_identical_switches_on_off(monkeypatch, kw):
    for p in _samples():
        out = {}
        for on in (False, True):
            _set(monkeypatch, on)
            try: out[on] = json.dumps(Q.collect(p, workers=4, **kw), sort_keys=True, default=str)
            except ValueError as ex: out[on] = 'ValueError %s' % ex          # class absent from this schema: must fail the same way
        assert out[True] == out[False], (p, kw)


def test_sheets_identical_switches_on_off(monkeypatch):
    for p in _samples():
        out = {}
        for on in (False, True):
            _set(monkeypatch, on); out[on] = json.dumps(Q.sheets(p, workers=4), sort_keys=True, default=str)
        assert out[True] == out[False], p
