#!/bin/bash
# re-run the studyx files killed under the 7 GB cap with a 16 GB cap on remote-host (results ~/.cache/rvt-ballet/sweep_studyx_031.jsonl there)
cd ~/src/rvt-ballet
~/.local/share/offload/h2run run vsweepstudyx --env occ --dir ~/src/rvt-ballet -- bash -c "RVT_SWEEP_OUT=~/.cache/rvt-ballet/sweep_studyx_031.jsonl RVT_SWEEP_SLICE=rvt-offload2.slice RVT_WORKERS=1 RVT_SWEEP_MEM=16G python tools/sweep.py $(for n in 031; do printf '~/scratch-famtest/studyx/studyx-%s.rvt ' $n; done)" 2>&1 | tail -3
