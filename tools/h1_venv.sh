#!/bin/sh
# host1: make bin/rvt-view / rvt-viewer find an interpreter (.venv/bin/python wrapper around the job env's python, which has aiohttp)
D="$(dirname "$(readlink -f "$0")")/.."; mkdir -p "$D/.venv/bin"; rm -f "$D/.venv/bin/python"
printf '#!/bin/sh\nexec %s "$@"\n' "$(command -v python)" > "$D/.venv/bin/python"; chmod +x "$D/.venv/bin/python"
