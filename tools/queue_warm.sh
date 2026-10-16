#!/bin/bash
# re-warm the sheets caches of the two big demo models on host1 once it has memory (rvt-view --prepare falls back to this when host1 is busy)
C=~/rvt-research/corpus
for i in $(seq 1 60); do
  out=$(RVT_WARM_NO_LOCAL=1 ~/src/rvt-viewer/bin/rvt-view --prepare $C/2024/43_Snowdon_Towers_Sample_Structural.rvt $C/2026/58_Snowdon_Towers_Sample_Facades.rvt 2>&1)
  echo "$(date +%T) $(echo "$out" | grep 'sheets:' | tr '\n' ' ')"
  echo "$out" | grep -q "warm failed" || break
  sleep 300
done
