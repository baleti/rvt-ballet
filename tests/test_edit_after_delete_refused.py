"""an edit on an element already queued for deletion is refused at edit time (was accepted and silently dropped by the save)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
from rvtballet.edit import EditError
def test_refuse():
    prior = [{'op': 'delete', 'eid': 5}]
    save._refuse_edit_of_deleted(prior, [{'op': 'set_string', 'eid': 6}])      # other element: fine
    save._refuse_edit_of_deleted(prior, [{'op': 'delete', 'eid': 5}])          # repeated delete: not an edit conflict
    for new in ([{'op': 'set_string', 'eid': 5}], [{'op': 'move', 'eid': 5}], [{'op': 'delete', 'eid': 7}, {'op': 'set_num', 'eid': 7}]):
        try: save._refuse_edit_of_deleted(prior, new)
        except EditError as e: assert 'already queued for deletion' in str(e)
        else: raise AssertionError('not refused: %r' % new)
if __name__ == '__main__': test_refuse(); print('OK')
