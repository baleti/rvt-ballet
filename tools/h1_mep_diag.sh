#!/bin/bash
# host1 diagnostic: convert one big file with per-stage RSS logging inside an 8 GB scope. usage: h1run run vmep --env occ --dir ~/src/rvt-viewer -- bash tools/h1_mep_diag.sh FILE
D="$(dirname "$(readlink -f "$0")")/.."; OUT=$HOME/offload/vmep-out; mkdir -p "$OUT"
RVT_LOG_RSS=1 RVT_CAPPED=1 systemd-run --user --scope -q --slice=rvt-offload.slice -p MemoryMax=${MEM:-8G} -p MemorySwapMax=0 python -c "import sys; sys.path.insert(0,'$D'); from rvtviewer.cli import main; main()" convert "$1" "$OUT/m" 2>&1 | grep -v "meshes [0-9]*[1-9]0/\|geometry [0-9]*/"
echo "EXIT ${PIPESTATUS[0]}"
