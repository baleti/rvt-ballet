#!/bin/bash
# find the slow mesh element in corpus-061, 063, 064 (same signature as corpus-008?) on host2, one after another; results ~/offload/slowmesh2.log there
cd ~/src/rvt-viewer
~/.local/share/offload/h2run run slowmesh2 --env occ --dir /home/user1/src/rvt-viewer -- bash -c "for n in 061 063 064; do echo FILE \$n; RVT_CORE_CACHE=/home/user1/offload/tscache python -u tools/find_slow_mesh.py /home/user1/scratch-famtest/corpus/corpus-\$n.rvt 20; done" 2>&1 | tail -2
