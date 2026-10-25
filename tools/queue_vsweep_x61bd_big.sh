#!/bin/bash
# re-run the studyx files killed under the 7 GB cap with a 16 GB cap on remote-host (results ~/.cache/rvt-viewer/sweep_studyx_big.jsonl there)
cd ~/src/rvt-viewer
~/.local/share/offload/h2run run vsweepstudyx --env occ --dir ~/src/rvt-viewer -- bash -c "RVT_SWEEP_OUT=~/.cache/rvt-viewer/sweep_studyx_big.jsonl RVT_SWEEP_SLICE=rvt-offload2.slice RVT_WORKERS=1 RVT_SWEEP_MEM=16G python tools/sweep.py $(for n in 019 022 023 030 038 041 065 066; do printf '~/scratch-famtest/studyx/studyx-%s.rvt ' $n; done)" 2>&1 | tail -3
