#!/bin/bash
cd ~/src/rvt-viewer
for i in $(seq 1 120); do
  out=$(~/.local/share/offload/h1run run vsweep4 --env occ --dir /home/user1/src/rvt-viewer -- bash -c "RVT_SWEEP_REDO=1 RVT_SWEEP_SLICE=rvt-offload.slice RVT_WORKERS=2 python tools/sweep.py" 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
