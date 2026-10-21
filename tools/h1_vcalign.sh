#!/bin/bash
# host1 job (h1run, env rvt): serve FILE and run vcalign.py on each VIEW id (grid / datum placement vs the reader's grids)
# usage: tools/h1_vcalign.sh FILE.rvt PORT VIEW_ID...
F="$1"; P="$2"; shift 2; D="$(dirname "$(readlink -f "$0")")/.."; export PATH="$HOME/vctl-pw/bin:$PATH" ALLOW_HOST3=1 RVT_SHEETS_PY=/home/user1/rvt-env/bin/python
cd "$D"; python -c "import sys; sys.path.insert(0, '$D'); from rvtviewer.cli import main; main()" open "$F" --no-browser --port "$P" > /tmp/vca-$P.log 2>&1 &
S=$!
for i in $(seq 1 900); do curl -sf "http://127.0.0.1:$P/api/models" > /dev/null && break; sleep 1; done
sleep 60
for v in "$@"; do echo "== view $v"; timeout 600 $HOME/vctl-pw/v/bin/python tools/vcalign.py "http://127.0.0.1:$P" "$v" 2>&1 | tail -8; done
kill $S
