"""backend RuntimeErrors (e.g. rvtedit's one-partition-per-save refusal) become EditError -> HTTP 400 'edit_error', never an unhandled 500. Uses a stand-in for rvtedit.Edit (no scene needed)."""
import os, sys, types, tempfile
os.environ['RVTBALLET_EDIT_BACKEND'] = 'rvtedit'
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import edit, save
class FakeEdit:
    def __init__(self, path):
        self.g = types.SimpleNamespace(e=types.SimpleNamespace(m=types.SimpleNamespace(parts={'Partitions/61': 1}), trace=lambda eid: ('Partitions/61',)))      # single partition: no grouping
    def set_string(self, eid, old, new):
        if eid == 2: raise RuntimeError('element 2 lives in Partitions/9 but this save edits Partitions/61 (multi-partition file: edit one partition per save; env PART)')
    def move(self, eid, dx, dy, dz):
        raise KeyError(eid)
    def save(self, dst): open(dst, 'wb').write(b'x')
fake = types.ModuleType('rvtedit'); fake.Edit = FakeEdit; sys.modules['rvtedit'] = fake
ok = edit.validate_op({'op': 'set_string', 'eid': 1, 'value': 'a'}); bad = edit.validate_op({'op': 'set_string', 'eid': 2, 'value': 'b'})
assert edit.apply(b'src', [ok]) == b'x'
try: edit.apply(b'src', [ok, bad]); raise SystemExit('FAIL: no error')
except edit.EditError as e: assert 'Partitions/9' in str(e) and 'refused by the edit backend' in str(e), e
mv = edit.validate_op({'op': 'move', 'eid': 5, 'dx': 1.0})
try: edit.apply(b'src', [mv]); raise SystemExit('FAIL: no error for move')
except edit.EditError as e: assert 'move' in str(e) and 'could not be applied' in str(e), e      # used to be a KeyError from the handler itself (no 'field' on move ops)
assert save.error_status(edit.EditError('x')) == (400, 'edit_error')
print('edit backend errors OK: multi-partition refusal -> EditError (400) with the backend message')
