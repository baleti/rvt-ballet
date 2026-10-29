#!/bin/sh
# whole save suite (needs ~/src/savegate and the write-lab scene; each test prints 'skip' when missing). usage: tests/run_save.sh
D="$(dirname "$(readlink -f "$0")")/.."; PY="$D/.venv/bin/python"; F=0
for t in test_save test_save_dest test_save_api test_save_overwrite test_save_versions test_save_restore test_save_paths test_save_concurrent test_save_edit test_save_reload test_save_restart test_save_locked test_save_nosavegate test_save_unreadable test_save_memory test_save_layout test_save_progress test_save_overwrite_roundtrip test_save_crash; do
  s=$(date +%s); out=$(nice "$PY" "$D/tests/$t.py" 2>&1 | tail -1 | cut -c1-110); echo "$t: $out ($(( $(date +%s)-s ))s)"
  case "$out" in *OK*|skip*) ;; *) F=1;; esac
done
[ $F = 0 ] && echo SAVE-SUITE OK || echo SAVE-SUITE FAILED; exit $F
