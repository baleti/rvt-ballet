#!/bin/bash
# real-world (studyx, anonymised ids) conversion sweep on remote-host via h2run: files in remote-host ~/scratch-famtest/studyx (copied remote-host -> remote-host), names in tools/studyx_ok.names; results ~/.cache/rvt-ballet/sweep_studyx.jsonl on remote-host (h2run pull .cache/rvt-ballet/sweep_studyx.jsonl)
cd ~/src/rvt-ballet
~/.local/share/offload/h2run run vsweepstudyx --env occ --dir ~/src/rvt-ballet -- bash -c "RVT_SWEEP_OUT=~/.cache/rvt-ballet/sweep_studyx.jsonl RVT_SWEEP_SLICE=rvt-offload2.slice RVT_WORKERS=1 RVT_SWEEP_MEM=7G python tools/sweep.py \$(sed 's#^#~/scratch-famtest/studyx/#' tools/studyx_ok.names)" 2>&1 | tail -3
