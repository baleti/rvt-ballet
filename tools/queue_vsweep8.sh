#!/bin/bash
# full-corpus conversion sweep on host1 after the 2026-10-22 reader parameter changes (regression check): results ~/.cache/rvt-viewer/sweep8.jsonl (finished files are skipped on resume); one worker
cd ~/src/rvt-viewer
for i in $(seq 1 200); do
  out=$(~/.local/share/offload/h1run run vsweep8 --env occ --dir /home/user1/src/rvt-viewer -- bash -c "RVT_SWEEP_REDO=1 RVT_SWEEP_OUT=~/.cache/rvt-viewer/sweep8.jsonl RVT_SWEEP_SLICE=rvt-offload.slice RVT_WORKERS=1 RVT_SWEEP_MEM=7G python tools/sweep.py" 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
