#!/bin/sh
# in-place save hardening suite (Autodesk 2024 sample, temp gates, no VM; ~20 min). Exit 1 if any test fails.
cd "$(dirname "$0")/.." || exit 2
rc=0
for t in test_inplace_damaged test_inplace_paths test_inplace_held test_inplace_crossdev test_inplace_signals test_inplace_enospc_e2e; do
  [ -f tests/$t.py ] || continue
  python3 -u tests/$t.py > /tmp/$t.log 2>&1 && echo "PASS $t" || { echo "FAIL $t (see /tmp/$t.log)"; rc=1; }
done
exit $rc
