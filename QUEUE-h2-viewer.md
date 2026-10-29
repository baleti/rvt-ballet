# QUEUE-h2-viewer (rvt-ballet viewer side, branch h2-viewer, 2026-10-29)
Goal: rvt-ballet opens, edits and SAVES / SAVE AS / OVERWRITES .rvt inline with zero corruption (output opens in the Revit VM without repair, untouched elements identical). Work top to bottom; commit tested work; aggregate numbers only (client files stay local).
Notes: ~/demo-state/PLAN-viewers-editors.md does NOT exist on this host (checked ~, ~, find /); sections 3-8 are taken from ~/demo-state/QUEUE-h2-native.md and ~/src/savegate (README, contract). Library = savegate (do not edit its tree, file requests). Writers/VM only via the write-lab harness. Any rvtballet/*.py edit changes viewer_stamp: re-run --prepare on the 3 demo files before moving demo-ready.

1. Savegate adapter in rvtballet/save.py: wrap sg.open_doc at model open (fingerprint at load), expose Doc per model id, no behaviour change when savegate missing. Test: unit test opens synthetic .rvt stub, fingerprint stored, import-optional.
2. Server API POST /api/m/{mid}/saveas {dest, overwrite:false}: calls sg.save_as with the manifest of recorded edits; returns {dest,size,sha256[:12],backup,verify}. Test: aiohttp test client against a synthetic file; source untouched (sha equal).
3. Server API POST /api/m/{mid}/save (overwrite) honouring Config(allow_overwrite) and the gate: GateClosed / OverwriteDisabled map to 409 with a readable message. Test matrix 2x2 (allow_overwrite x gate open).
4. Conflict handling: file changed on disk since load -> 409 Conflict {reload|force}; force only with explicit confirm=true. Test: touch the source between load and save.
5. UI commands SAVE AS / SAVE / SAVE! (toolbar + command line in web/): result panel shows dest, size, sha prefix, backup path, verify line; VerifyFailed lists first differing keys. Playwright check with forced VerifyFailed, original untouched.
6. Unsupported versions (pre-2024 not writable, whatever the writable list says): refusal names the version and the writable list; UI disables buttons with a tooltip. Test per year 2017..2026 on the synthetic stub + corpus headers.
7. RESTORE / RECOVER: list backups, restore byte-identical, journal listed after SIGKILL of the server. pytest + curl check.
8. Edit model: parameter edit op (string + integer on one element) recorded in the manifest (stream: keys per savegate contract), undo pops the op. Test: manifest content, undo drops it from next save.
9. Edit ops beyond parameters supported by write-lab (delete element, move element): inventory table docs/EDIT-COVERAGE.md (element class x op x writer support); unsupported combos refuse with a clear message. Table checked by test.
10. Round-trip identity matrix through the server API: 10 corpus projects (2024, 2026), load-save-load with empty manifest; assert zero verify differences, report counts and seconds (aggregate only).
11. Revit VM open check of every matrix output through the write-lab harness; table OPEN / OPENFAIL / REPAIRED. Gate evidence file written only if 100% clean.
12. Edit fuzz chains via API (parameter edits/deletes, 20 ops, 200 chains on a small corpus subset): every result passes library verify; classify VerifyFailed/SaveError; no HTTP 500. File each failure class in NEEDS-FROM-WRITER.
13. Repeated save cycles 50x SAVEAS->open->SAVEAS on 3 files: element table equal to generation 0, size stable. Report drift.
14. Path edge cases: unicode + spaces, long path, read-only dir, other filesystem, same-as-source dest: nothing written on failure, no leftover .sgtmp/lock. Parametrised pytest.
15. Kill-mid-save + ENOSPC (small tmpfs) via savegate _step hooks against the server path: target absent or complete, source intact, journal shows stage.
16. Large files: SAVEAS of the 3 largest local projects under a 5 GB cap, peak RSS and verify seconds; progress line in UI if verify > 60 s.
17. Viewer reload after save: the saved file re-opens in the viewer, cache key distinct from source, edited parameter visible in the inspector. Playwright.
18. tests/swarm/README.md (PLAN section 4 equivalent): element classes x versions, exact commands, failure-report format (NEEDS-FROM-*.md line).
19. CI: savegate-backed tests unskipped using generated synthetic stubs, no corpus.
20. Sync to remote-host after each commit batch; publish scan-only counts into PROGRESS.md.

Status log (append below):
1. DONE 2026-10-29: rvtballet/save.py SaveSessions + tests/test_save.py (not yet wired to server)
2. DONE 2026-10-29: POST /api/m/{mid}/saveas (identity save; edits come with item 8); tests/test_save_api.py: source sha unchanged, output sha equal, exists->409, overwrite->backup, bad body 400, unknown mid 404, no leftover temp/lock. NOTE rvtballet/*.py changed => demo models need --prepare before demo-ready moves.
3+4. DONE 2026-10-29: POST /api/m/{mid}/save (overwrite) + GET /api/m/{mid}/saveinfo (opens doc = load-time fingerprint, reports allow_overwrite/gate_open); env RVTBALLET_ALLOW_OVERWRITE=1; tests/test_save_overwrite.py 2x2 matrix (disabled/gate_closed 409, open 200), conflict 409, force needs confirm=true (400), force+confirm 200. Tests isolate journal/backup dirs.
