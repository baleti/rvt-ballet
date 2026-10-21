#!/bin/bash
# retry loop: model cached on host3 (capped), sheets warm on host1 once its gate opens; stops when neither model reports 'warm failed'
C=~/rvt-research/corpus
for i in $(seq 1 100); do
  out=$(RVT_WARM_NO_LOCAL=1 RVT_MEM_CAP=3500M ALLOW_HOST3=1 ~/src/rvt-viewer/tools/capped.sh ~/src/rvt-viewer/bin/rvt-view --prepare $C/2024/43_Snowdon_Towers_Sample_Structural.rvt $C/2026/58_Snowdon_Towers_Sample_Facades.rvt 2>&1)
  echo "$(date +%T) $(echo "$out" | grep -a 'rvt: \|\.rvt:' | tr '\n' ' ')"
  echo "$out" | grep -aq "warm failed" || break
  sleep 300
done
