#!/bin/bash
# reference hl_score on the synthetic pairs (seeds 1-3): prints the result line and the seconds (host1 job, env occ)
cd ~/src/rvt-ballet
for s in 1 2 3; do d=/tmp/hlsynth$s; python tools/hl_synth.py $s $d >/dev/null; t0=$SECONDS; python tools/hl_score_ref.py $d/revit.png $d/ours.png; echo "seed $s ref seconds $((SECONDS - t0))"; done
