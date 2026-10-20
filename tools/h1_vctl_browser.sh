#!/bin/bash
# remote-host job (h1run, env rvt): serve FILE with rvt-view, run vctltest.py and vcui.py on VIEW with a headless chromium from ~/vctl-pw (playwright headless shell, wrapper bin/chromium)
# usage: tools/h1_vctl_browser.sh FILE.rvt VIEW_ID [PORT]
F="$1"; V="$2"; P="${3:-8899}"; D="$(dirname "$(readlink -f "$0")")/.."; export PATH="$HOME/vctl-pw/bin:$PATH" ALLOW_remote-host=1 RVT_SHEETS_PY=~/rvt-env/bin/python
cd "$D"; python -c "import sys; sys.path.insert(0, '$D'); from rvtviewer.cli import main; main()" open "$F" --no-browser --port "$P" > /tmp/vcb-$P.log 2>&1 &
S=$!
for i in $(seq 1 900); do curl -sf "http://127.0.0.1:$P/api/models" > /dev/null && break; sleep 1; done
sleep 60
$HOME/vctl-pw/v/bin/python tools/vctltest.py "http://127.0.0.1:$P" "$V" 2>&1 | tail -25
$HOME/vctl-pw/v/bin/python tools/vcui.py "http://127.0.0.1:$P" "$V" 2>&1 | tail -15
kill $S
