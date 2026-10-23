#!/bin/sh
# unit tests + smoke test on a converted model (default: newest in the cache). Everything runs niced.
D="$(dirname "$(readlink -f "$0")")/.."; PY="$D/.venv/bin/python"
nice "$PY" "$D/tests/test_geom.py" && nice "$PY" "$D/tests/test_surfaces.py" && nice "$PY" "$D/tests/test_pipeline.py" && nice "$PY" "$D/tests/test_plugins.py" || exit 1
M="${1:-$(ls -dt $HOME/.cache/rvt-viewer/models/*/ | grep -v "\.tmp/\|/trunc-" | head -1)}"
nice "$PY" "$D/tests/smoke.py" "$M"; R=$?
"$PY" "$D/tools/cleanup_browsers.py"; exit $R
