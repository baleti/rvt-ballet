"""save._MEMBER_WORKER: the 'no design option' sentinel is -1 in both id widths (2**64-1 for 8-byte ids, 2**32-1 for the 2017/2018 4-byte layout); neither may count as a design option, a real option id must. Pure unit test (rvt_xcache stubbed)."""
import sys, os, io, json, types, contextlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
def run(opt):
    m = types.ModuleType('rvt_xcache'); m.get_x_ro = lambda p: {'recs': {(7, 'FamilyInstance'): {'fields': {'m_designOptionId': opt}}}}
    sys.modules['rvt_xcache'] = m; sys.argv = ['w', 'x', '[7]']; buf = io.StringIO()
    with contextlib.redirect_stdout(buf): exec(compile(save._MEMBER_WORKER, 'w', 'exec'), {'__name__': '__main__'})
    return json.loads(buf.getvalue().splitlines()[-1])['7'][0]['options']
assert run(4294967295) == [], 'FAIL 4-byte -1 counted as option'
assert run(2 ** 64 - 1) == [], 'FAIL 8-byte -1 counted as option'
assert run(123456) == [123456], 'FAIL real option dropped'
print('OK')
