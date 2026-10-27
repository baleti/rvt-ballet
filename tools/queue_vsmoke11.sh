#!/bin/bash
# retry loop: demo_smoke on the two Snowdon demo files on host1 once its memory gate opens (result: h1run tail vsmoke11)
cd ~/src/rvt-ballet
for i in $(seq 1 200); do
  out=$(~/.local/share/offload/h1run run vsmoke11 --env occ --dir /home/user1/src/rvt-ballet -- bash -c "tools/h1_venv.sh; tools/demo_smoke.sh ~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt 8941; tools/demo_smoke.sh ~/rvt-research/corpus/2026/58_Snowdon_Towers_Sample_Facades.rvt 8942" 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
