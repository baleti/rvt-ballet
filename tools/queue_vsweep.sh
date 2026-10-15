#!/bin/bash
# resume the full-corpus sweep on host1 (results in ~/.cache/rvt-viewer/sweep4.jsonl, finished files are skipped); one worker: two rme files together exceed the 9 GB slice
cd ~/src/rvt-viewer
for i in $(seq 1 120); do
  out=$(~/.local/share/offload/h1run run vsweep5 --env occ --dir /home/user1/src/rvt-viewer -- bash -c "RVT_SWEEP_OUT=~/.cache/rvt-viewer/sweep4.jsonl RVT_SWEEP_SLICE=rvt-offload.slice RVT_WORKERS=1 RVT_SWEEP_MEM=7G python tools/sweep.py" 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
