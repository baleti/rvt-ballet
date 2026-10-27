#!/bin/sh
# per-class acceptance metrics on ALL corpus .rvt files 2020-2026: ONE file at a time, under a 3.5 GB cap + nice, never started while MemAvailable < 5 GB. Skips files that already have a result.
D="$(dirname "$(readlink -f "$0")")/.."; OUT="$HOME/.cache/rvt-ballet/accept"; mkdir -p "$OUT"
for f in $HOME/rvt-research/corpus/202[0-6]/*.rvt; do
  y=$(basename "$(dirname "$f")"); s=$(basename "$f" .rvt)
  [ -f "$OUT/${y}_${s}.json" ] && continue
  while [ "$(awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo)" -lt 5 ]; do echo "waiting: MemAvailable < 5 GB" >> /tmp/accept_all.log; sleep 60; done
  RVT_MEM_CAP=3500M "$D/tools/capped.sh" "$D/.venv/bin/python" "$D/tools/accept_eval.py" "$f" >> /tmp/accept_all.log 2>&1
done
