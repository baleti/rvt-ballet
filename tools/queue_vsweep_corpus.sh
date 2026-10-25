#!/bin/bash
# real-world (corpus, anonymised ids) conversion sweep on host2 via h2run: files in host2 ~/scratch-famtest/corpus (copied host1 -> host2), names in tools/corpus.names; results ~/.cache/rvt-viewer/sweep_corpus.jsonl on host2 (h2run pull .cache/rvt-viewer/sweep_corpus.jsonl)
cd ~/src/rvt-viewer
~/.local/share/offload/h2run run vsweepcorpus --env occ --dir /home/user1/src/rvt-viewer -- bash -c "RVT_SWEEP_OUT=~/.cache/rvt-viewer/sweep_corpus.jsonl RVT_SWEEP_SLICE=rvt-offload2.slice RVT_WORKERS=1 RVT_SWEEP_MEM=7G python tools/sweep.py \$(sed 's#^#/home/user1/scratch-famtest/corpus/#' tools/corpus.names)" 2>&1 | tail -3
