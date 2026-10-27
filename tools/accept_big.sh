#!/bin/sh
# files that do not fit the 3 GB budget in one process (listed in accept/SKIPPED.txt): evaluate in TWO halves, one process at a time, each under 3 GB:
#   analytic classes (walls, floors, roofs, MEP curves ...) with the viewer context, then everything else through the reader geometry API only.
D="$(dirname "$(readlink -f "$0")")/.."; OUT="$HOME/.cache/rvt-ballet/accept"
while read n; do
  y=${n%%_*}; s=${n#*_}; f=$HOME/rvt-research/corpus/$y/$s.rvt; [ -f "$f" ] || continue
  for mode in analytic mesh; do
    [ "$mode" = analytic ] && [ -f "$OUT/${n}__analytic.json" ] && continue; [ "$mode" = mesh ] && [ -f "$OUT/${n}__mesh.json" ] && continue
    while [ "$(awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo)" -lt 5 ]; do sleep 120; done
    if [ "$mode" = analytic ]; then RVT_ANALYTIC_ONLY=1 RVT_RSS_BUDGET=2.7 RVT_MEM_CAP=3000M "$D/tools/capped.sh" "$D/.venv/bin/python" "$D/tools/accept_eval.py" "$f" >> /tmp/accept_big.log 2>&1
    else RVT_RSS_BUDGET=2.7 RVT_MEM_CAP=3000M "$D/tools/capped.sh" "$D/.venv/bin/python" "$D/tools/accept_eval.py" --mesh "$f" >> /tmp/accept_big.log 2>&1; fi
  done
done < "$OUT/SKIPPED.txt"
