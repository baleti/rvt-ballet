from rvtballet.save import risky_membership as r
m = {5: ['dimensioned by 3 dimension(s)', 'hosts 10 element(s)']}
assert r(m, [{'eid': 5, 'op': 'delete'}]) == {5: ['dimensioned by 3 dimension(s)']}
assert r(m, [{'eid': 5, 'op': 'set_string'}]) == {}
print('PASS')
