#!/bin/bash
# retry loop: tools/vis_cats.py on host1 (result: h1run tail viscats)
cd ~/src/rvt-ballet
for i in $(seq 1 200); do
  out=$(~/.local/share/offload/h1run run viscats --env occ --dir /home/user1/src/rvt-ballet -- /home/user1/rvt-env/bin/python tools/vis_cats.py 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
