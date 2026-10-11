#!/bin/sh
# second pass for the files that did not fit the 3.5 GB budget: ONE at a time, 5.5 GB cap, only while MemAvailable >= 9 GB (else waits). Say so in the report: these need > 3.5 GB (reader context + geometry context).
D="$(dirname "$(readlink -f "$0")")/.."; OUT="$HOME/.cache/rvt-viewer/accept"
for f in $HOME/rvt-research/corpus/202[0-6]/*.rvt; do
  y=$(basename "$(dirname "$f")"); s=$(basename "$f" .rvt)
  [ -f "$OUT/${y}_${s}.json" ] && continue
  while [ "$(awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo)" -lt 9 ]; do echo "retry waiting: MemAvailable < 9 GB" >> /tmp/accept_retry.log; sleep 120; done
  RVT_RSS_BUDGET=5.0 RVT_MEM_CAP=5500M "$D/tools/capped.sh" "$D/.venv/bin/python" "$D/tools/accept_eval.py" "$f" >> /tmp/accept_retry.log 2>&1
done
