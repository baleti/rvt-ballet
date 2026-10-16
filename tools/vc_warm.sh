#!/bin/sh
# tools/vc_warm.sh FILE.rvt [NAME]: pre-generate the view-control scenes of every plan/section view of FILE on host1 (capped slice), then pull the cache to host3.
# The cache key is content based (file name+size, rvt-sheets code, worker code), so scenes warmed on host1 are valid on host3. Needs the repo synced to host1 (rsync below).
F=$(readlink -f "$1"); N=${2:-vcwarm_$(basename "$F" .rvt | cut -c1-20)}; D=$(cd "$(dirname "$0")/.." && pwd)
ssh host1 "mkdir -p $D" && rsync -a --exclude=.git --exclude=__pycache__ --exclude='.venv*' --exclude=node_modules "$D/" "host1:$D/"
~/.local/share/offload/h1run run "$N" --dir "$D" -- python "$D/tools/vc_warm_sheets.py" "$F"
echo "then: ~/.local/share/offload/h1run tail $N ; ~/.local/share/offload/h1run pull .cache/rvt-sheets/<dir from the last log line>"
