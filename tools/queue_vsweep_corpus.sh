#!/bin/bash
# real-world (corpus, anonymised ids) conversion sweep on host1: files live in host1 ~/scratch-famtest/corpus; results ~/.cache/rvt-viewer/sweep_corpus.jsonl on host1; one worker
cd ~/src/rvt-viewer
for i in $(seq 1 200); do
  out=$(~/.local/share/offload/h1run run vsweepcorpus --env occ --dir /home/user1/src/rvt-viewer -- bash -c "RVT_SWEEP_OUT=~/.cache/rvt-viewer/sweep_corpus.jsonl RVT_SWEEP_SLICE=rvt-offload.slice RVT_WORKERS=1 RVT_SWEEP_MEM=7G python tools/sweep.py ~/scratch-famtest/corpus/*.rvt" 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
