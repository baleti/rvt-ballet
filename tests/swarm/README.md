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

Suggested corpus per group: the writer scenes `~/rvt-research/write-lab/scenes/20{24,26}_writer_*.rte` (synthetic, safe to publish numbers for) and, locally only, delivered client files of the same years.

## Failure report
Append one line to `NEEDS-FROM-WRITER.md` (writer-side cause: record edit, stamp, dependents) or `NEEDS-FROM-READER.md` (reader/verify-side cause) in this repo:

`- DATE ACCOUNT group=G7 year=2024 files=N ok=M class=<verify_failed|VerifyFailed key list head|SaveError|HTTP 500|REVIT OPENFAIL|REPAIRED> repro=<exact command> evidence=<aggregate numbers only, never client names>`

A save that writes a file Revit cannot open without repair is a **stop-the-line** failure: say so at the start of the line and do not open the gate (`savegate gate open rvt YEAR --evidence FILE` only with a 100 % clean matrix).
