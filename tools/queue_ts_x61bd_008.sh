#!/bin/bash
# cold conversion of studyx studyx-008 on remote-host with a wall-clock stamp on every progress line (which stage takes the 1100 s?): ~/offload/ts_studyx_008.txt there
cd ~/src/rvt-ballet
~/.local/share/offload/h2run run tsstudyx --env occ --dir ~/src/rvt-ballet -- bash -c "rm -rf ~/.cache/rvt-ballet/ts-work ~/offload/tscache; export RVT_NO_GEOM_CACHE=1 RVT_CORE_CACHE=~/offload/tscache RVT_CAPPED=1; python -u -c \"import sys; sys.path.insert(0,'.'); from rvtballet.cli import main; main(['convert','~/scratch-famtest/studyx/studyx-008.rvt','~/.cache/rvt-ballet/ts-work'])\" 2>&1 | while IFS= read -r l; do echo \"\$(date +%T) \$l\"; done  > ~/offload/ts_studyx_008.txt" 2>&1 | tail -2
