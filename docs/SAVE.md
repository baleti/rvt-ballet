# Saving from rvt-ballet (SAVE AS / SAVE / edits)

Status: offline-verified with the savegate library; **no edited file produced by the viewer has yet been confirmed to open in Revit** (VM queue, see QUEUE-h2-viewer.md items 11/22). Overwrite stays disabled by default.

Requires `~/src/savegate` (or an installed `savegate`) and the write-lab (`~/rvt-research/write-lab`, env `RVTBALLET_WRITELAB`). Without them the viewer runs unchanged and every save endpoint answers 501.

Writable Revit years: those in `savegate.adapters.RVT_WRITABLE` (2024, 2026 today). Other years are refused with HTTP 415 naming the version and the list.

## Endpoints (all per model id `mid`)
| endpoint | purpose |
|---|---|
| `GET /api/m/{mid}/saveinfo` | opens the save session (fingerprint = load time): `{available, open, version, size, sha256, allow_overwrite, gate_open, pending_edits}` |
| `POST /api/m/{mid}/edit` `{op:'set_string', eid, value, field?, match?}` | record an edit (trial-replayed at once); fields: ParamValueAString.m_value, DatumPlane.m_text, DBView.m_viewName, SymbolInfo.m_name |
| `POST /api/m/{mid}/edit/undo`, `GET /api/m/{mid}/edits` | pop / list pending edits (memory only, dropped on viewer restart) |
| `POST /api/m/{mid}/saveas` `{dest, overwrite?}` | write a copy; never touches the source; returns dest, size, sha256[:12], backup, verify report |
| `POST /api/m/{mid}/save` `{force?, confirm?}` | overwrite the source (needs `RVTBALLET_ALLOW_OVERWRITE=1` **and** an open oracle gate); `force` needs `confirm:true` |
| `GET /api/m/{mid}/backups`, `POST /api/m/{mid}/restore` `{n, confirm:true}` | list / restore backups (current file is backed up first) |
| `GET /api/recover` | journals of sessions that never closed (crash / kill) |

Error codes (JSON `{ok:false, code, error, report?}`): `bad_dest` 400, `edit_error` 400, `conflict` 409 (file changed since load), `gate_closed` / `overwrite_disabled` / `exists` 409, `locked` 423 (another save running or lock held), `verify_failed` 422 (output differs outside the declared edit; nothing written; `report.unexpected` lists the first keys), `unsupported_version` 415, `disk_error` 507, `unavailable` 501.

## Guarantees checked by tests (`tests/run_save.sh`, ~2 min)
Source never changes on SAVE AS; atomic write with backup; element-level verify of every output (declared edits only); crash at each step and ENOSPC leave source/target consistent; concurrent saves refused; hostile destinations refused before any work.

## Not guaranteed / open
Revit opening the output (VM pending); edits other than string fields; edits whose dependents change (e.g. Level rename: refused by verify); parameter edits addressed by name (writer op missing, so the UI has no edit control); Windows/macOS behaviour.
