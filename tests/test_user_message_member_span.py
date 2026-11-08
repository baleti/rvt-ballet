"""refusal text for the member_span verify failure (growing a string) explains it and says the file is untouched"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet import save
class VerifyFailed(Exception): pass
def test_member_span_message():
    e = VerifyFailed("verify failed: 1 differences outside the declared edit (first: ('member_span', 'Partitions/64 member 36 differs over 131028 bytes (max 8198)'))")
    m = save.user_message(e, 422)
    assert 'same length' in m and 'not touched' in m, m
    m2 = save.user_message(VerifyFailed('verify failed: 2 differences (first: (x))'), 422); assert 'same length' not in m2 and m2.endswith('not touched')

def test_delete_dependents_message():
    e = VerifyFailed('read-back of the edited element(s) failed: delete changed the parameters of 9 surviving element(s) (e.g. 356, 359, 360); the model file was not touched')
    m = save.user_message(e, 422)
    assert 'depend on the element' in m and 'nothing was changed' in m and m.count('not touched') == 1, m

if __name__ == '__main__': test_member_span_message(); test_delete_dependents_message(); print('OK')
