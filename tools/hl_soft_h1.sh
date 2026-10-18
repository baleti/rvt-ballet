#!/bin/sh
# host1: vg3d JSON per HLR view (rvt-sheets resolve_view via rvtviewer/vg3d_worker.py) + software hidden-line render + F1.  usage (via h1run, env rvt): tools/hl_soft_h1.sh NAME FILE.rvt MODELDIR
NAME=$1; FILE=$2; MODEL=$3; H=$HOME; export PYTHONPATH=$H/src/rvt-sheets:$H/rvt-research${PYTHONPATH:+:$PYTHONPATH}; D=$(dirname "$0")
mkdir -p $H/review-compare/vg3d/$NAME
for vid in $(grep -v '^#' $H/review-compare/revit/$NAME/cameras.tsv | grep 'style=HLR' | cut -f1); do
  [ -s $H/review-compare/vg3d/$NAME/$vid.json ] || python3 $D/../rvtviewer/vg3d_worker.py $FILE $vid > $H/review-compare/vg3d/$NAME/$vid.json 2>$H/review-compare/vg3d/$NAME/$vid.err || { echo "vg3d failed for view $vid: $(tail -2 $H/review-compare/vg3d/$NAME/$vid.err)"; rm -f $H/review-compare/vg3d/$NAME/$vid.json; }
done
python3 $D/hl_soft_all.py $NAME $MODEL
