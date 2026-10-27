#!/bin/bash
# retry loop: re-prepare (convert + sheets warm) the two Snowdon demo models on host1 after a converter change, then smoke them (result: h1run tail prep2)
cd ~/src/rvt-ballet; C=~/rvt-research/corpus
for i in $(seq 1 200); do
  out=$(~/.local/share/offload/h1run run prep2 --env occ --dir /home/user1/src/rvt-ballet -- bash -c "tools/h1_venv.sh; RVT_WARM_NO_LOCAL=1 bin/rvt-view --prepare $C/2024/43_Snowdon_Towers_Sample_Structural.rvt $C/2026/58_Snowdon_Towers_Sample_Facades.rvt; tools/demo_smoke.sh $C/2024/43_Snowdon_Towers_Sample_Structural.rvt 8961; tools/demo_smoke.sh $C/2026/58_Snowdon_Towers_Sample_Facades.rvt 8962" 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
