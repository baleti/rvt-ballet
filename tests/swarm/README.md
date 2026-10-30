# rvt-ballet save test swarm

Goal: opening, editing and saving .rvt through rvt-ballet never corrupts a file: every output opens in Revit without repair, untouched elements are identical.
Pick one **group** below, run its command on any host that has `~/src/savegate`, `~/rvt-research/write-lab` and the venv (`.venv/bin/python`), and report one line (format at the end). Client files stay local: report aggregates only.
Revit VM checks go **only** through the write-lab harness (`~/rvt-research/write-lab/tools/open_test.py YEAR FILE TAG`, see its WRITER.md); never start a VM yourself.

Each test isolates its journal and backup dirs (`SAVEGATE_JOURNAL`, `SAVEGATE_CACHE` in a temp dir) and never writes next to your inputs. Element-level verify costs ~35 s per save on a 5.6k-element scene: give tests 120 s+.

| group | what it proves | command | writable years |
|---|---|---|---|
| G1 api-saveas | identity SAVE AS: output bytes == source, source untouched, exists -> 409, bad body 400 | `.venv/bin/python tests/test_save_api.py` | 2024 |
| G2 overwrite-gate | SAVE: allow_overwrite x gate 2x2, conflict 409, force needs confirm | `.venv/bin/python tests/test_save_overwrite.py` | 2024 |
| G3 versions | years 2017..2026: writable -> 200, others -> 415 naming version + writable list | `.venv/bin/python tests/test_save_versions.py` | 2024, 2026 |
| G4 restore-recover | backups listed, restore byte-identical, SIGKILL journal listed | `.venv/bin/python tests/test_save_restore.py` | 2024 |
| G5 edit | string-parameter edit declared in manifest, verify 0 undeclared, undo; dependent-changing edit refused | `.venv/bin/python tests/test_save_edit.py` | 2024 |
| G6 ui | real clicks: Save as, panel, forced VerifyFailed, conflict buttons | `.venv/bin/python tools/uitest_save.py CONVERTED_MODELDIR 89NN OUTDIR` (convert first: `./rvt-ballet convert FILE OUTDIR`) | 2024 |
| G7 identity-matrix | N files x 2 generations through the API, aggregate OK count | `.venv/bin/python tools/save_matrix.py OUT.json FILE...` | 2024, 2026 |
| G8 edit-coverage | which element classes carry which validated edit fields | `.venv/bin/python tools/edit_coverage.py FILE [OUT.md]` | 2024, 2026 |
| G9 revit-open | outputs of G7/G5 opened in the Revit VM (audit) | write-lab harness, queue item 11 of QUEUE-h2-viewer.md | 2024, 2026 |

| G10 whole-suite | all 31 offline save tests in one run (throwaway TMPDIR, snapshot cache off) | `tests/run_save.sh` (~7 min) | 2024 |
| G11 fuzz | random edit chains: no HTTP 500, source never changes, verify refusals classified | `.venv/bin/python tools/save_fuzz.py SRC MODELDIR CHAINS SEED OUT.json` then `tools/fuzz_classes.py MODELDIR OUT.json` (MODELDIR = `./rvt-ballet convert SRC DIR`) | 2024 |
| G12 ops | numeric / name-addressed / move / delete ops (rvtedit backend): `tests/test_save_setnum.py`, `test_save_param_name.py`, `test_save_move.py`, `test_save_delete.py`, `test_edit_pairing.py` | `RVTBALLET_EDIT_BACKEND=rvtedit` is set inside the tests | 2024 |
| G13 limits | memory cap, limited verification, worker failure classes, disk-full, kill at each step | `tests/test_save_memcap.py`, `test_save_light.py`, `test_save_review2.py`, `test_save_crash.py` | 2024 |
| G14 real-identity | REAL projects (local files only!): identity SAVE AS x2 generations with element-level verify; aggregate OK count, seconds, peak RSS | `.venv/bin/python tools/save_matrix.py OUT.json FILE...` (ascending size; a 14 GB RSS watchdog is advisable: a 64 MB project needs more) | 2024, 2026 |
| G15 real-edit | one by-name Comments edit / one move / overwrite+backup+restore / 3-round overwrite chain on a REAL project (a COPY for overwrite) | `tools/save_real_edit.py`, `save_real_move.py`, `save_real_overwrite.py`, `save_real_chain.py` | 2024, 2026 |
| G16 real-limited | LIMITED verification on a project too large for the element dump; equivalence with the full verify on a small one | `tools/save_real_light.py FILE`, `tools/save_real_equiv.py FILE` (KEEP_DIR=dir keeps the output locally for Revit) | 2024, 2026 |
| G17 real-revit | outputs of G14-G16 in Revit, audit ON, WITH the untouched original as control first | write-lab `campaign/stages.api_stage(2026, FILE, True, TAG)` via `open_audit`-style wrapper; Revit 2026 upgrades 2024 files on open | 2024 (as 2026 upgrade) |

Safety rules for REAL files: client files stay on the local machine; reports carry aggregates only (counts, seconds, MB, GB, sizes in MB): no file names, paths, element names or ids; run overwrite tests on a COPY with a temp gate (`SAVEGATE_GATE`, `RVTBALLET_ALLOW_OVERWRITE=1` set inside the process, never the real gate); delete the copies and kept outputs when done; the shared /tmp is a tmpfs that fills up: use `TMPDIR` on a disk path for big files.
Known harness limit (2026-10-30): the Revit audit dump throws "The input curve is not bound" on some real projects even for the UNTOUCHED original; always run the control first and treat a failing control as "no verdict", not as a failure of the edit.

Suggested corpus per group: the writer scenes `~/rvt-research/write-lab/scenes/20{24,26}_writer_*.rte` (synthetic, safe to publish numbers for) and, locally only, delivered client files of the same years.

## Failure report
Append one line to `NEEDS-FROM-WRITER.md` (writer-side cause: record edit, stamp, dependents) or `NEEDS-FROM-READER.md` (reader/verify-side cause) in this repo:

`- DATE ACCOUNT group=G7 year=2024 files=N ok=M class=<verify_failed|VerifyFailed key list head|SaveError|HTTP 500|REVIT OPENFAIL|REPAIRED> repro=<exact command> evidence=<aggregate numbers only, never client names>`

A save that writes a file Revit cannot open without repair is a **stop-the-line** failure: say so at the start of the line and do not open the gate (`savegate gate open rvt YEAR --evidence FILE` only with a 100 % clean matrix).
