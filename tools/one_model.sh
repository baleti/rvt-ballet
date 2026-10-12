#!/bin/sh
# convert ONE corpus model with a given cap (default 6G), after checking MemAvailable (>= MIN_GB, default 8): tools/one_model.sh FILE.rvt OUTDIR [CAP]
D="$(dirname "$(readlink -f "$0")")/.."; MIN=${MIN_GB:-8}
while [ "$(awk '/MemAvailable/ {print int($2/1048576)}' /proc/meminfo)" -lt "$MIN" ]; do echo "waiting for MemAvailable >= $MIN GB" >&2; sleep 60; done
RVT_MEM_CAP=${3:-6G} "$D/tools/capped.sh" "$D/.venv/bin/python" -c "import sys; sys.path.insert(0,'$D'); from rvtviewer import cli; print(cli.ensure(sys.argv[1], True))" "$1"
