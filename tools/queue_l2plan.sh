#!/bin/bash
# retry loop: hidden-line shot of Snowdon Structural L2 plan 581543 on host1 + hl_score_fast vs Revit export (result: h1run tail l2plan)
cd ~/src/rvt-viewer
R=~/review-compare/3d_43_Snowdon_Towers_Sample_Structural/581543_L2_hidden_line__plan__revit.png
scp -q $R host1:/tmp/l2_revit.png
for i in $(seq 1 200); do
  out=$(~/.local/share/offload/h1run run l2plan --env occ --dir /home/user1/src/rvt-viewer -- bash -c "tools/h1_venv.sh; export PATH=\$HOME/vctl-pw/bin:\$PATH ALLOW_HOST3=1 RVT_SHEETS_PY=/home/user1/rvt-env/bin/python; python tools/shot3d.py ~/rvt-research/corpus/2024/43_Snowdon_Towers_Sample_Structural.rvt 581543 - /tmp/l2_ours.png --clean --size 2400x1369 --style hidden --vg 581543 && python tools/hl_score_fast.py /tmp/l2_revit.png /tmp/l2_ours.png" 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
