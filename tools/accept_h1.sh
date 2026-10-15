#!/bin/bash
# per-class acceptance on host1 (run through ~/.local/share/offload/h1run, env occ): ONE corpus file at a time, results in ~/.cache/rvt-viewer/accept/ on host1 (pull with h1run pull .cache/rvt-viewer/accept)
# usage (host3): h1run run accept --env occ --dir ~/src/rvt-viewer -- bash tools/accept_h1.sh [YEAR ...]
D="$(dirname "$(readlink -f "$0")")/.."; OUT="$HOME/.cache/rvt-viewer/accept"; mkdir -p "$OUT"; PY=python
YEARS=${@:-2020 2021 2022 2023 2024 2025 2026}
for y in $YEARS; do for f in $HOME/rvt-research/corpus/$y/*.rvt; do
  s=$(basename "$f" .rvt); [ -f "$OUT/${y}_${s}.json" ] && continue
  echo "== $y $s $(date +%T)"
  RVT_RSS_BUDGET=${RVT_RSS_BUDGET:-3.6} $PY "$D/tools/accept_eval.py" "$f" 2>&1 | grep -E "^OK|ABORT|Error|Traceback" 
  if [ ! -f "$OUT/${y}_${s}.json" ]; then echo "mesh-mode retry $y $s"; RVT_RSS_BUDGET=2.7 $PY "$D/tools/accept_eval.py" "$f" --mesh 2>&1 | grep -E "^OK|ABORT|Error" ; fi
done; done
echo ACCEPTDONE
