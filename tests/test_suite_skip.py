"""rvt_suite: a cell whose latest PASS has the same writer stamp + sample sha is skipped; changed stamp, dirty tree, FAIL or missing stamp are re-run."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import rvt_suite as S
S.LEDGER = tempfile.mkdtemp() + '/l.jsonl'
S.put_ledger('r1', 'k', 'PASS', 'x', 'abc/123')
assert S.already_proven('k', 'abc/123')
assert not S.already_proven('k', 'abd/123') and not S.already_proven('k', 'abc/124')      # writer or sample changed
assert not S.already_proven('k', 'abc+dirty/123')
S.put_ledger('r2', 'k', 'FAIL', 'x', 'abc/123'); assert not S.already_proven('k', 'abc/123')      # latest is FAIL
S.put_ledger('r3', 'k2', 'PASS', 'x'); assert not S.already_proven('k2', '/')      # old rows without stamp never skip
S.put_ledger('r4', 'k3', 'PASS', 'x', 'abc+dirty/1'); assert not S.already_proven('k3', 'abc+dirty/1')
print('OK')
