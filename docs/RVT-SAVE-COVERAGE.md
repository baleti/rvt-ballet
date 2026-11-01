# rvt-ballet in-place save: edit coverage by element class (Autodesk samples only)

Method (tools/rvt_class_pass.py): per class, up to 4 edits on different elements (string parameter, numeric parameter, move, name field) in ONE session, SAVE AS (element verify + read-back), SAVE! in place on a private copy (gate opened in a temp file only; overwrite stays OFF by default), then check: verify 0 unexpected; re-read parameters (only the declared ones changed); SAVE! bytes == SAVE AS bytes; backup restore == original sha256; untouched elements % (tools/rvt_untouched_report.py). Revit judge: tools/rvt_vm_open.py (offline VM, audit on).

Writable years: 2024, 2026 (older years are refused by design).

| file | class | result |
|---|---|---|
| 2024 HVAC (22 MB) | FamilyInstance, LinearDimString | move OK |
| 2024 HVAC | MaterialElem | string + number OK |
| 2024 HVAC | RoomElem | string OK (reader alias Number == Room Number|String is not a side effect) |
| 2024 HVAC | Grid | name OK |
| 2024 HVAC | Level | rename refused by the gate: 14 undeclared dependents |
| 2024 Structural (28 MB) | SWall | number + move OK, 99.988 % elements untouched |
| 2024 Construction template | Family num, FamilySymbol / DBView3d name, MaterialElem | OK |
| 2024 Construction template | DBViewPlan / DBViewSection / Level rename | refused (dependents) |
| 2024 hosted2 scene | SWall num+move, RoomElem string, LinearDimString move, Family num | OK |
| 2024 hosted2 scene | FamilyInstance string+move | SAVE AS OK, SAVE! refused layout_changed (deliberate) |

Revit VM (2024, audit on): HVAC FamilyInstance move, RoomElem string, MaterialElem outputs open, no repair prompt; the unedited original shows the same enclosed-region warnings.

Severity-1 found and fixed: a non-BMP (emoji) string value was accepted by the gate and left the edited element with half its parameters (26 -> 13). Now refused at the input (edit._check_text) and by a read-back of every edited element before writing (save._readback). Regression: tests/test_edit_text.py, tests/test_save_readback.py.

Gate probes (tests/test_save_escape.py, tools/rvt_flip_sweep.py): 14 hand tampers + 60 random bit flips handed to the gate as writer output: all refused except changes confined to CFB header padding / free sectors (streams byte-identical), which are accepted and classified PADDING_ONLY.

Known gaps: classes with no accepted edit yet (text notes, tags, ducts, viewports, sheets, floors on the samples tried); renames with dependents; third in-place save on one file (layout_changed).

Further gate probes (c5x): tests/test_save_escape_semantic.py (valid 2-move output with a manifest declaring one mover, nothing, or the wrong element: all refused, source intact). Sources truncated by 512 B / 4 KB / 5% are refused at open. Source with 4 KB trailing zeros: no-edit SAVE AS accepted, trailing bytes carried through unchanged. Source with a corrupted FAT: redirected/swapped links refused by the output check, an early end-of-chain accepted and carried through unchanged (the gate proves output == edit of source, not source health). Warm-cache no-edit SAVE AS on a 5 MB 2024 scene: 16.5 s cold, 4.5 s repeat (output verify kept).

Update 2026-11-01 (c4x-rvtmatrix, Autodesk-sample and synthetic scenes only):
- Revit VM (offline, audit on) opens with no dialogs, cmp 0/0: in-place SAVE! outputs of Comments/Bool/Int/Double edits on the 5 MB 2024 template, in-place Comments on the 2026 sheets scene; SAVE AS outputs on the 2026 sheets scene (view rename, FamilyInstance, RoomElem string, LinearDimString) and the 2024 view rename.
- View rename: the "other" elements that change are name aliases only (View Name, View Name|String, Sheet Name, Panel Schedule Name), gate verify 0; the class-pass driver reports them as declared dependents.
- Intermittent: one in-place Comments save on the 2024 hosted scene was refused (verify_failed, 62 differences outside the edit, model untouched); 7 later attempts (warm and cold cache) all passed. Cause unknown, still open.
- Pending VM verdict: in-place SAVE! output of the 2024 hosted scene. Pending: 40-flip sweep on a 2026 file.
