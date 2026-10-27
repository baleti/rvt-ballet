#!/bin/bash
# retry loop: hl_score of the viewer's Residential building section vs Revit's export on host1 (result: h1run tail hlscore1)
cd ~/src/rvt-ballet
scp -q ~/review-compare/2020_Residential/228085_building_section_section__revit.png host1:/tmp/hls_revit.png
scp -q ~/review-compare/viewer-shots/res_building_section.png host1:/tmp/hls_ours.png
for i in $(seq 1 200); do
  out=$(~/.local/share/offload/h1run run hlscore1 --env occ --dir /home/user1/src/rvt-ballet -- python tools/hl_score.py /tmp/hls_revit.png /tmp/hls_ours.png 2>&1)
  echo "$(date +%T) $out" | tail -2
  echo "$out" | grep -q "busy\|refus" || break
  sleep 300
done
