#!/bin/bash
# full-corpus conversion sweep on host1 after the 2026-10-21 converter changes (64 pattern grids, view family): results ~/.cache/rvt-ballet/sweep7.jsonl (finished files are skipped on resume); one worker
cd ~/src/rvt-ballet
for i in $(seq 1 200); do
  out=$(~/.local/share/offload/h1run run vsweep7 --env occ --dir /home/user1/src/rvt-ballet -- bash -c "RVT_SWEEP_REDO=1 RVT_SWEEP_OUT=~/.cache/rvt-ballet/sweep7.jsonl RVT_SWEEP_SLICE=rvt-offload.slice RVT_WORKERS=1 RVT_SWEEP_MEM=7G python tools/sweep.py" 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
