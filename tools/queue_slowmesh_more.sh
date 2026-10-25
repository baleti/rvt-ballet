#!/bin/bash
# find the slow mesh element in studyx-061, 063, 064 (same signature as studyx-008?) on remote-host, one after another; results ~/offload/slowmesh2.log there
cd ~/src/rvt-viewer
~/.local/share/offload/h2run run slowmesh2 --env occ --dir ~/src/rvt-viewer -- bash -c "for n in 061 063 064; do echo FILE \$n; RVT_CORE_CACHE=~/offload/tscache python -u tools/find_slow_mesh.py ~/scratch-famtest/studyx/studyx-\$n.rvt 20; done" 2>&1 | tail -2
