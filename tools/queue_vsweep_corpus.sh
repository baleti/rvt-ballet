#!/bin/bash
# re-run the corpus files that timed out or were killed (061 063 064) with a 16 GB cap on host2 (results ~/.cache/rvt-viewer/sweep_corpus.jsonl there)
cd ~/src/rvt-viewer
~/.local/share/offload/h2run run vsweepcorpus --env occ --dir /home/user1/src/rvt-viewer -- bash -c "RVT_SWEEP_OUT=~/.cache/rvt-viewer/sweep_corpus.jsonl RVT_SWEEP_SLICE=rvt-offload2.slice RVT_WORKERS=1 RVT_SWEEP_TIMEOUT=3600 RVT_SWEEP_MEM=16G python tools/sweep.py $(for n in 061 063 064; do printf '/home/user1/scratch-famtest/corpus/corpus-%s.rvt ' $n; done)" 2>&1 | tail -3
