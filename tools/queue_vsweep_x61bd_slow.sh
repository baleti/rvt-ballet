#!/bin/bash
# re-run the studyx files that timed out or were killed (061 063 064) with a 16 GB cap on remote-host (results ~/.cache/rvt-ballet/sweep_studyx_slow.jsonl there)
cd ~/src/rvt-ballet
~/.local/share/offload/h2run run vsweepstudyx --env occ --dir ~/src/rvt-ballet -- bash -c "RVT_SWEEP_OUT=~/.cache/rvt-ballet/sweep_studyx_slow.jsonl RVT_SWEEP_SLICE=rvt-offload2.slice RVT_WORKERS=1 RVT_SWEEP_TIMEOUT=3600 RVT_SWEEP_MEM=16G python tools/sweep.py $(for n in 061 063 064; do printf '~/scratch-famtest/studyx/studyx-%s.rvt ' $n; done)" 2>&1 | tail -3
