"""diff --ops matcher (synthetic dicts, no .rvt bytes): exact match passes; wrong value, extra change, missing op, truncated record all fail. Run: python tests/test_diff_ops.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from rvtballet.infocli import _ops, _same

def rec(**ch): return {'class': 'FamilyInstance', 'fields_changed': len(ch), 'changed': ch}
def bad(r): return len(r['unmatched_changes']) + len(r['missing_ops'])

ops = [{'id': 5, 'path': '.a[0]', 'old': 1.0, 'new': 3.0}, {'id': 5, 'path': '.b', 'new': 'x'}]
ok = {'differing': {'5': rec(**{'.a[0]': ['1.0', '3.0'], '.b': ["'y'", "'x'"]})}}
assert bad(_ops(ok, ops)) == 0
assert bad(_ops({'differing': {'5': rec(**{'.a[0]': ['1.0', '3.5'], '.b': ["'y'", "'x'"]})}}, ops)) == 1, 'wrong new value'
assert bad(_ops({'differing': {'5': rec(**{'.a[0]': ['2.0', '3.0'], '.b': ["'y'", "'x'"]})}}, ops)) == 1, 'wrong old value'
assert bad(_ops({'differing': {'5': rec(**{'.a[0]': ['1.0', '3.0'], '.b': ["'y'", "'x'"], '.c': ['0', '1']})}}, ops)) == 1, 'extra change'
assert bad(_ops({'differing': {'5': rec(**{'.a[0]': ['1.0', '3.0']})}}, ops)) == 1, 'missing op'
assert bad(_ops({'differing': {'5': rec(**{'.a[0]': ['1.0', '3.0'], '.b': ["'y'", "'x'"]}), '9': rec(**{'.z': ['0', '1']})}}, ops)) == 1, 'other element changed'
t = rec(**{'.a[0]': ['1.0', '3.0'], '.b': ["'y'", "'x'"]}); t['fields_changed'] = 99
assert bad(_ops({'differing': {'5': t}}, ops)) == 1, 'truncated record'
assert _same('1.0000000001', 1.0) and not _same('1.001', 1.0) and _same("'x'", 'x')
print('diff --ops matcher ok')
