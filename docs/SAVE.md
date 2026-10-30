# Saving from rvt-ballet (SAVE AS / SAVE / edits)

Status: offline-verified with the savegate library. Revit evidence so far (shared write-lab harness, Revit 2024, audit OFF, synthetic write-lab scene only): all six viewer-produced edited files opened at least once (three single edits incl. unicode and a 200-character value, and generations 1, 4 and 8 of an eight-save chain; several needed retries because of guest failures). Failures seen were guest/transport problems (the unmodified original also failed twice). Revit 2026: four viewer-edited 2026 files also opened (a single edit and generations 1-3 of a chain, including the re-paged generation 3; the unmodified control opened 2/2). Audit-ON (SaveAs + reopen element lists equal in every case): all four Revit 2026 files passed (single edit and generations 1-3 of the chain incl. the re-paged gen3), each on the first attempt; Revit 2024 single0 and single1 passed (others hit guest failures, the unmodified control passed audit-on on its 2nd try). The layout guard is therefore a precaution without Revit evidence of harm. NOT yet done: audit-ON opens, more 2026 edits, real client projects, edit kinds other than string parameters. Overwrite stays disabled by default.

Requires `~/src/savegate` (or an installed `savegate`) and the write-lab (`~/rvt-research/write-lab`, env `RVTBALLET_WRITELAB`). Without them the viewer runs unchanged and every save endpoint answers 501.

Writable Revit years: those in `savegate.adapters.RVT_WRITABLE` (2024, 2026 today). Other years are refused with HTTP 415 naming the version and the list.

## Endpoints (all per model id `mid`)
| endpoint | purpose |
|---|---|
| `GET /api/m/{mid}/saveinfo` | opens the save session (fingerprint = load time): `{available, open, version, size, sha256, allow_overwrite, gate_open, pending_edits}` |
| `POST /api/m/{mid}/edit` `{op:'set_string', eid, value, field?, match?}` or (rvtedit backend only) `{op:'set_num', eid, param|pid, value, kind:'Double'|'Int'}` | record an edit (trial-replayed at once); fields: ParamValueAString.m_value, DatumPlane.m_text, DBView.m_viewName, SymbolInfo.m_name |
| `POST /api/m/{mid}/edit/undo`, `GET /api/m/{mid}/edits` | pop / list pending edits (memory only, dropped on viewer restart) |
| `POST /api/m/{mid}/saveas` `{dest, overwrite?}` | write a copy; never touches the source; returns dest, size, sha256[:12], backup, verify report |
| `POST /api/m/{mid}/save` `{force?, confirm?}` | overwrite the source (needs `RVTBALLET_ALLOW_OVERWRITE=1` **and** an open oracle gate); `force` needs `confirm:true` |
| `GET /api/m/{mid}/backups`, `POST /api/m/{mid}/restore` `{n, confirm:true}` | list / restore backups (current file is backed up first) |
| `GET /api/recover` | journals of sessions that never closed (crash / kill) |

Error codes (JSON `{ok:false, code, error, report?}`): `bad_dest` 400, `edit_error` 400, `conflict` 409 (file changed since load), `gate_closed` / `overwrite_disabled` / `exists` 409, `locked` 423 (another save running or lock held), `verify_failed` 422, `output_unreadable` 422, `layout_changed` 409 (overwrite refused when a partition stream's page layout would change: SAVE AS warns instead; override RVTBALLET_ALLOW_LAYOUT_CHANGE=1), `too_big` 507, `bad_dest` 400 (output differs outside the declared edit; nothing written; `report.unexpected` lists the first keys), `unsupported_version` 415, `disk_error` 507, `unavailable` 501.

Edit backend: `RVTBALLET_EDIT_BACKEND=wledit` (default, write-lab `Editor`) or `rvtedit` (edit-lab `rvtedit.Edit`, same string edit; path `RVTBALLET_EDITLAB`). One string edit gives byte-identical output on both; with two edits the bytes differ (parameter values read back identical, one element's record hash differs: open question for rvtedit2). `set_num` is wired (rvtedit backend only; a parameter NAME is resolved to the single id stored on that element, ambiguous or not-stored names are refused with 400; values are in Revit internal units, e.g. feet for lengths). Delete, move and rotate exist only in rvtedit and are not wired yet.

## Guarantees checked by tests (`tests/run_save.sh`, ~2 min)
Source never changes on SAVE AS; atomic write with backup; element-level verify of every output (declared edits only); crash at each step and ENOSPC leave source/target consistent; concurrent saves refused; hostile destinations refused before any work.

## Not guaranteed / open
Revit opening outputs beyond the four files above (audit-on, 2026, real projects); edits other than string fields; edits whose dependents change (e.g. Level rename: refused by verify); parameter edits addressed by name (writer op missing, so the UI has no edit control); Windows/macOS behaviour.
