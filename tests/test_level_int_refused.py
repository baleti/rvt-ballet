import pytest
from rvtballet import edit


class _E:
    def trace(self, eid): return (None, None, {'class': 'Level'}, [])


class _G: e = _E()


class _Ed: g = _G()


def test_level_int_param_refused():
    o = {'op': 'set_num', 'eid': 329, 'param': 'Building Story', 'kind': 'Int', 'value': 0, 'pid': -1007111}
    with pytest.raises(edit.EditError, match='Level'):
        edit._set_num_by_pid(_Ed(), o)
