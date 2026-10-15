#!/bin/sh
# tools/vc_warm.sh FILE.rvt [NAME]: pre-generate the view-control scenes of every plan/section view of FILE on remote-host (capped slice), then pull the cache to remote-host.
# The cache key is content based (file name+size, rvt-sheets code, worker code), so scenes warmed on remote-host are valid on remote-host. Needs the repo synced to remote-host (rsync below).
F=$(readlink -f "$1"); N=${2:-vcwarm_$(basename "$F" .rvt | cut -c1-20)}; D=$(cd "$(dirname "$0")/.." && pwd)
ssh remote-host "mkdir -p $D" && rsync -a --exclude=.git --exclude=__pycache__ --exclude='.venv*' --exclude=node_modules "$D/" "remote-host:$D/"
~/.local/share/offload/h1run run "$N" --dir "$D" -- python "$D/rvtviewer/vscene_worker.py" "$F" --warm
echo "then: ~/.local/share/offload/h1run tail $N ; ~/.local/share/offload/h1run pull .cache/rvt-viewer/vscene"
