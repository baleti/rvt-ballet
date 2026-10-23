#!/bin/bash
# retry loop: hidden-line edge angle sweep (tools/hl_soft_sweep.py in the hl worktree) on host1 once its memory gate opens (result: h1run tail hlsweep2)
rsync -a --exclude=.git ~/src/rvt-viewer-hl/tools host1:src/rvt-viewer-hl/ 2>/dev/null
for i in $(seq 1 200); do
  out=$(HL_SWEEP_GRID=30:0.01,45:0.01 ~/.local/share/offload/h1run run hlsweep2 --env rvt -- sh -c "cd ~/src/rvt-viewer-hl && M=\$(ls -dt ~/.cache/rvt-viewer/models/43_Snowdon_Towers_Sample_Structural-*/meta.json | head -1 | xargs dirname); python3 tools/hl_soft_sweep.py 43_Snowdon_Towers_Sample_Structural \$M" 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
