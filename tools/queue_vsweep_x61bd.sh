#!/bin/bash
# real-world (studyx, anonymised ids) conversion sweep on remote-host: files live in remote-host ~/scratch-famtest/studyx; results ~/.cache/rvt-viewer/sweep_studyx.jsonl on remote-host; one worker
cd ~/src/rvt-viewer
for i in $(seq 1 200); do
  out=$(~/.local/share/offload/h1run run vsweepstudyx --env occ --dir ~/src/rvt-viewer -- bash -c "RVT_SWEEP_OUT=~/.cache/rvt-viewer/sweep_studyx.jsonl RVT_SWEEP_SLICE=rvt-offload.slice RVT_WORKERS=1 RVT_SWEEP_MEM=7G python tools/sweep.py ~/scratch-famtest/studyx/*.rvt" 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
