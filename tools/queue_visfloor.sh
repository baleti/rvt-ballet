#!/bin/bash
cd ~/src/rvt-viewer
for i in $(seq 1 200); do
  out=$(~/.local/share/offload/h1run run visfloor --env occ --dir /home/user1/src/rvt-viewer -- /home/user1/rvt-env/bin/python tools/vis_floor.py 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
