# HANDOFF h2-viewer (rvt-ballet SAVE / SAVE AS / OVERWRITE) - 2026-10-29

Goal: rvt-ballet opens, edits and saves .rvt inline with zero corruption. Branch `h2-viewer`. Queue: `QUEUE-h2-viewer.md` (status log at the bottom, newest last). API/guarantees: `docs/SAVE.md`. Coverage: `docs/EDIT-COVERAGE.md`. Swarm brief: `tests/swarm/README.md`.

## What exists (all offline-tested; Revit-verified only where stated)
- `rvtballet/save.py` (savegate wiring, element-level verify with a content-hash snapshot cache, error mapping, destination/memory/layout guards, backups/restore/recover), `rvtballet/edit.py` (set_string ops replayed on the loaded bytes with write-lab `wledit.Editor`), server endpoints in `rvtballet/server.py`, UI in `web/save.js` (Save, Save as, Backups, result panel, progress).
- Suite: `tests/run_save.sh` (18 tests, ~3 min, needs `~/src/savegate` + `~/rvt-research/write-lab`; skips otherwise). Browser: `tools/uitest_save.py`, `tools/uitest_save2.py`, `tools/jstest_save.py` (headless Chromium; no node on these hosts). Stress/fuzz: `tools/save_matrix.py`, `save_fuzz.py`, `save_chain.py`, `save_reload_check.py`, `save_big.py`, `save_years.py`, `edit_coverage.py`, `fuzz_classes.py`.
- Safety defaults: overwrite OFF (`RVTBALLET_ALLOW_OVERWRITE=1` + an open oracle gate needed; the real gate file does not exist and was never opened). SAVE AS warns, overwrite is refused when a partition stream's page layout changes (`RVTBALLET_ALLOW_LAYOUT_CHANGE=1` overrides).

## Measured so far (synthetic write-lab scenes, 2024 and 2026 only)
Identity matrix 10/10 byte-identical; fuzz seeds 1-5 (60 chains): 0 HTTP 500 after the fix, 0 source changes, ~16% of chains refused by verify (undeclared changes on same-class elements: writer issue); 10/10 random edits re-convert with exactly the edited parameter differing; crash/ENOSPC/lock/concurrency/destination/memory cases pass; 305 MB container saves in 20 s at 2.4 GB RSS.
**Revit verdicts (2024 guest, shared harness): 2 files OPEN ok (chain gen1, single1). Everything else is inconclusive: the guest returned hang/crash for 4 files INCLUDING the unmodified original (control).** Nothing is Revit-verified beyond those 2 opens; audit-ON not run yet. Verdict files: scratchpad `vmq/verdicts*.txt`, `vmq26/verdicts5.txt` (2026 guest); runners `vmq/run*.sh` chain retries + audit + control (scratchpad is session-local: re-create from QUEUE item 22 if gone).

## Open / blocked
1. Revit verdicts: wait for control try 2, retries (run2), audit-on (run3), 2026 guest (run5). Only a file that fails repeatedly while the control passes counts against the writer. Do not claim "verified" beyond what the verdict files show.
2. Writer (NEEDS-FROM-WRITER.md): name-addressed parameter op (blocks the inspector editor), int param op, dependents rule (Level rename, same-class neighbours changing), second-generation re-paging (full_pages +1, cap_last 0; mechanism measured, fix proposed; link to Revit failures UNPROVEN), combination bug seed 4 chain 7.
3. Savegate (~/demo-state/NEEDS-FROM-SAVEGATE.md): snapshot cache in core, verify progress callback, typed error for reader crashes, explicit-adapter sniff hole, memory ~8x file size.
4. Not possible from this host: remote-host sync (does not resolve), CI green on runners (no push), node tests (no node; `tests/js/save.test.mjs` unrun), Windows/macOS behaviour, real client 2024/2026 projects (none here: run `tools/save_matrix.py` and `tools/save_years.py` locally).
5. Any `rvtballet/*.py` edit changes viewer_stamp: re-run `--prepare` on the 3 demo models before moving demo-ready (not done after the save work: save code does not touch conversion, but the stamp includes the package).
