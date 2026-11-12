# In-place save: what was tested (Autodesk samples, private copies, temporary gate files)

Method: every run used a private copy of an Autodesk Snowdon Towers HVAC sample (2024, 2025 or 2026) and a per-run gate file (`SAVEGATE_GATE`), so the real overwrite gate stayed closed. Verdicts come from (a) the editor's own verification, (b) an independent record diff (`rvt-ballet diff --all-records --ops`), (c) `rvt-ballet check` (the save gate's damage detector) and (d) opening the result in the offline Revit VM with an API readback. Each result is a single file.

| Hazard | Result |
|---|---|
| success path | saved, backup byte-identical to the original, no temp files |
| 3 chained in-place saves | every previous version recoverable; final file = exactly the 3 edits; opens in Revit |
| edits to two elements in one save | both land exactly in Revit |
| kill -9 during verify (4 moments), at the commit line (2) and 20 ms after (1), plus 16 timed kills | target is either the untouched original or a complete file; the 3 commit-window files open in Revit 2024 and read back the edit |
| external change during the save (append, byte flip) | refused as conflict, the external change survives; mtime-only touch saves |
| two simultaneous saves of one file | one wins, one refused (locked); no mixed file |
| stale / foreign lock files | live holder and other host refused; dead pid and old foreign lock taken over |
| damaged source (byte flip, truncation, zeroed blocks, header flip) | refused, file untouched (tests/test_inplace_damaged.py) |
| out of space at backup write / at rename | refused, original intact (tests/test_inplace_enospc_e2e.py) |
| read-only file / read-only directory | refused, untouched |
| symlink / hard link | symlink: real file saved, link kept; hard link: other names keep old content and a warning says so |
| odd path characters, 225-251 character names | saved, backup name shortened to fit |
| gate absent / wrong year / invalid JSON / empty / env switch off | refused (fails closed) |
| output path hazards for SAVE AS (same file, existing, symlink, hard link) | refused |
| restore of the oldest backup | original bytes; a damaged backup is refused |

Known limits: single files and one sample family; the Revit result concerns one element; power loss without fsync, network file systems, worksharing and groups are not covered; 2025 in-place stays gated in production.

Real Revit failures found (not corruption): `--set-num` on Space load parameters is accepted as verified but Revit ignores the stored value (dashboard FAIL x2). A move with a vertical component and moves of structural columns are refused by the editor's own verification.
