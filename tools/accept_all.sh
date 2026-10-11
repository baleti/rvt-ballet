#!/bin/sh
# per-class acceptance metrics on ALL corpus .rvt files 2020-2026 (2 at a time, each under a 5 GB cap + nice); results in ~/.cache/rvt-viewer/accept/
D="$(dirname "$(readlink -f "$0")")/.."
ls ~/rvt-research/corpus/202[0-6]/*.rvt | xargs -P 2 -I{} sh -c "RVT_MEM_CAP=5G $D/tools/capped.sh $D/.venv/bin/python $D/tools/accept_eval.py {} >> ${TMPDIR:-/tmp}/accept_all.log 2>&1"
