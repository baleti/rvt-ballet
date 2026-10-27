"""build._sign_material_ids: unsigned 64-bit material ids from rvt_elemmesh become signed (NEEDS-FROM-READER item 30)"""
import os, sys, types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_sign():
    EM = types.ModuleType('rvt_elemmesh'); vals = iter([2 ** 64 - 4000010, 5, None, -3])
    EM._material_of = lambda *a, **k: next(vals)
    sys.modules['rvt_elemmesh'] = EM
    from rvtballet import build
    build._sign_material_ids(); build._sign_material_ids()
    f = EM._material_of
    assert [f(), f(), f(), f()] == [-4000010, 5, None, -3]
    assert f._signed

if __name__ == '__main__':
    test_sign(); print('ok')
