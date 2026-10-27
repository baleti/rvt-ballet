#!/bin/bash
# cold conversion of corpus corpus-008 on host2 with a wall-clock stamp on every progress line (which stage takes the 1100 s?): ~/offload/ts_corpus.txt there
cd ~/src/rvt-ballet
~/.local/share/offload/h2run run tscorpus --env occ --dir /home/user1/src/rvt-ballet -- bash -c "rm -rf /home/user1/.cache/rvt-ballet/ts-work /home/user1/offload/tscache; export RVT_NO_GEOM_CACHE=1 RVT_CORE_CACHE=/home/user1/offload/tscache RVT_CAPPED=1; python -u -c \"import sys; sys.path.insert(0,'.'); from rvtballet.cli import main; main(['convert','/home/user1/scratch-famtest/corpus/corpus-008.rvt','/home/user1/.cache/rvt-ballet/ts-work'])\" 2>&1 | while IFS= read -r l; do echo \"\$(date +%T) \$l\"; done  > /home/user1/offload/ts_corpus.txt" 2>&1 | tail -2
