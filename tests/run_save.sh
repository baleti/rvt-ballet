#!/bin/sh
# whole save suite (needs ~/src/savegate and the write-lab scene; each test prints 'skip' when missing). usage: tests/run_save.sh
D="$(dirname "$(readlink -f "$0")")/.."; PY="$D/.venv/bin/python"; F=0
# all temp files of the suite go to one throwaway directory that is removed at the end (the tests used to leave ~20 MB-200 MB dirs in /tmp each)
# the persistent snapshot cache would turn every repeat save into a cache hit and hide what the cold-path tests check: off by default here (test_save_snapcache sets its own directory)
export RVTBALLET_SNAPSHOT_CACHE=0
T="$(mktemp -d)"; export TMPDIR="$T"; trap 'rm -rf "$T"' EXIT INT TERM
# the conversions the tests run fill the SHARED caches (~/.cache/rvt-ballet geom-*.pkl 190 MB each, ~/.cache/rvt-core): keep both inside the throwaway directory so nothing survives the run (host disk emergency 2026-11-01)
export RVT_BALLET_CACHE="$T/ballet-cache" RVT_CORE_CACHE="$T/core-cache" 
for t in test_save test_save_dest test_save_api test_save_overwrite test_save_versions test_save_restore test_save_paths test_save_symlink_source test_save_concurrent test_save_edit test_edit_pairing test_save_setnum test_save_param_name test_save_delete test_save_move test_save_rotate test_save_derived test_save_sameelement test_save_readonly test_save_readonly_dir test_save_reload test_save_restart test_save_locked test_edit_backend_errors test_save_nosavegate test_save_unreadable test_save_memory test_save_memcap test_save_snaptimeout test_save_light test_save_not_applied test_save_review2 test_save_review test_save_layout test_save_progress test_save_overwrite_roundtrip test_save_crash test_save_snapcache test_save_readback test_edit_text; do
  s=$(date +%s); out=$(nice "$PY" "$D/tests/$t.py" 2>&1 | tail -1 | cut -c1-110); echo "$t: $out ($(( $(date +%s)-s ))s)"
  case "$out" in *OK*|skip*) ;; *) F=1;; esac
done
[ $F = 0 ] && echo SAVE-SUITE OK || echo SAVE-SUITE FAILED; exit $F
