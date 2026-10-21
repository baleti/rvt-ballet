#!/bin/bash
# remote-host job (h1run, env rvt): serve FILE and open every drawable plan / section / drafting / legend view with vcsweep.py (JS exceptions per view); VC_LIGHT=1 hides the model under the drawing
# usage: tools/h1_vcsweep.sh FILE.rvt PORT
F="$1"; P="$2"; D="$(dirname "$(readlink -f "$0")")/.."; export PATH="$HOME/vctl-pw/bin:$PATH" ALLOW_remote-host=1 RVT_SHEETS_PY=~/rvt-env/bin/python
cd "$D"; python -c "import sys; sys.path.insert(0, '$D'); from rvtviewer.cli import main; main()" open "$F" --no-browser --port "$P" > /tmp/vcs-$P.log 2>&1 &
S=$!
for i in $(seq 1 900); do curl -sf "http://127.0.0.1:$P/api/models" > /dev/null && break; sleep 1; done
sleep 60
timeout 14400 $HOME/vctl-pw/v/bin/python -u tools/vcsweep.py "http://127.0.0.1:$P" 2>&1
kill $S
