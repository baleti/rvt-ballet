#!/bin/sh
# convert one rosetta file (fresh) and compare it with its Revit oracle (gt_geom): tools/rosetta.sh NAME   (e.g. 2024_wall_curved_base); work dir: ${ROSETTA_WORK:-/tmp/rvtv-rosetta}
D="$(dirname "$(readlink -f "$0")")/.."; W=${ROSETTA_WORK:-/tmp/rvtv-rosetta}; N=$1; mkdir -p "$W"
RVT_NOFAST=${RVT_NOFAST:-1} RVT_MEM_CAP=${RVT_MEM_CAP:-6G} "$D/tools/capped.sh" "$D/.venv/bin/python" -c "import sys; sys.path.insert(0,'$D'); from rvtviewer import build; build.convert(sys.argv[1], sys.argv[2], log=lambda *a: None)" "$HOME/rosetta/$N.rte" "$W/out_$N" > /dev/null 2>&1
RVT_MEM_CAP=${RVT_MEM_CAP:-6G} "$D/tools/capped.sh" "$D/.venv/bin/python" "$D/tools/compare_gt.py" "$W/out_$N" "$HOME/rvt-research/gt_geom" 2>&1 | tail -1
python3 - "$W/out_$N" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]+'/meta.json')); c=json.load(open(sys.argv[1]+'/compare.json'))['elements']; E=m['elements']
for i,v in c.items():
    if E[int(i)][1] not in ('Material','BasePoint','CoordinateSystemDisplayElem','ProfileRefPlane'): print('  ',E[int(i)][1],E[int(i)][3],v)
PY
