#!/bin/bash
# fresh software hidden-line renders + F1 for Snowdon 43 (2024) on host2: convert, then tools/hl_soft_all.py (browser free). Renders land in ~/review-compare/viewer/<name>/<vid>__soft.png on host2 (h2run pull review-compare/viewer/<name>)
cd ~/src/rvt-ballet
N=43_Snowdon_Towers_Sample_Structural
~/.local/share/offload/h2run run hlsoft43 --env occ --dir /home/user1/src/rvt-ballet -- bash -c "RVT_CAPPED=1 python -c \"import sys; sys.path.insert(0,'.'); from rvtballet.cli import main; main(['convert','/home/user1/rvt-research/corpus/2024/$N.rvt','/home/user1/.cache/rvt-ballet/hl-$N'])\" && python tools/hl_soft_all.py $N /home/user1/.cache/rvt-ballet/hl-$N" 2>&1 | tail -2
