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
