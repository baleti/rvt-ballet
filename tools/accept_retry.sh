#!/bin/sh
# second pass for files that did not fit the first budget: ONE at a time, 3 GB cap (budget 2.7 GB RSS), only while MemAvailable >= 5 GB. Files that still exceed it are recorded in accept/SKIPPED.txt (not retried).
D="$(dirname "$(readlink -f "$0")")/.."; OUT="$HOME/.cache/rvt-ballet/accept"; mkdir -p "$OUT"
for f in $HOME/rvt-research/corpus/202[0-6]/*.rvt; do
  y=$(basename "$(dirname "$f")"); s=$(basename "$f" .rvt)
  [ -f "$OUT/${y}_${s}.json" ] && continue
  grep -q "^${y}_${s}$" "$OUT/SKIPPED.txt" 2>/dev/null && continue
  while [ "$(awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo)" -lt 5 ]; do echo "retry waiting: MemAvailable < 5 GB" >> /tmp/accept_retry.log; sleep 120; done
  RVT_RSS_BUDGET=2.7 RVT_MEM_CAP=3000M "$D/tools/capped.sh" "$D/.venv/bin/python" "$D/tools/accept_eval.py" "$f" >> /tmp/accept_retry.log 2>&1
  [ -f "$OUT/${y}_${s}.json" ] || echo "${y}_${s}" >> "$OUT/SKIPPED.txt"
done
