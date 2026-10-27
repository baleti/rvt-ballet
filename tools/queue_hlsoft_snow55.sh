#!/bin/bash
# fresh software hidden-line renders + F1 for Snowdon 43 (2024) on remote-host: convert, then tools/hl_soft_all.py (browser free). Renders land in ~/review-compare/viewer/<name>/<vid>__soft.png on remote-host (h2run pull review-compare/viewer/<name>)
cd ~/src/rvt-ballet
N=55_Snowdon_Towers_Sample_Structural
~/.local/share/offload/h2run run hlsoft55 --env occ --dir ~/src/rvt-ballet -- bash -c "RVT_CAPPED=1 python -c \"import sys; sys.path.insert(0,'.'); from rvtballet.cli import main; main(['convert','~/rvt-research/corpus/2026/$N.rvt','~/.cache/rvt-ballet/hl-$N'])\" && python tools/hl_soft_all.py $N ~/.cache/rvt-ballet/hl-$N" 2>&1 | tail -2
