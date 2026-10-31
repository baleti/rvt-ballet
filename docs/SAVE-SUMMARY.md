# rvt-ballet saving: what it can and cannot do (status 2026-10-31)

Written for the orchestrator and users. Details: `docs/SAVE.md`; evidence log: `QUEUE-h2-viewer.md`; hand-off: `HANDOFF-h2-viewer.md`.

## What works
- **Open, edit, SAVE AS** of Revit **2024 and 2026** project files (`.rvt`). The source file is never touched by SAVE AS.
- **Edit kinds:** string parameter (by name), numeric parameter (Double / Int, by name), move, rotate, delete of a leaf element (delete is opt-in).
- **In place SAVE (overwrite)** is off by default; when enabled it needs the open savegate gate, writes an atomic backup first, can be restored, and is refused for workshared models.
- **Every output is verified before it is written:** element-by-element comparison against the source (only the declared edits may differ), read-back of the edited values, page-layout check, memory-capped verification worker with a time limit. A failed check refuses the save and writes nothing.
- **Crash safety:** SIGKILL at every save step on real projects: the source is always exactly the old or exactly the new file (36 kills, 0 mixed); disk full / read-only / bad destination refuse cleanly.

## Evidence (real projects, aggregate)
- 13 local 2024 projects (7.6 - 232 MB); 7 pass the current savegate guards; the rest are refused by the build-stamp guard (question filed).
- About 150 mixed edit chains on two real projects (string, numeric, move, rotate, delete): all saved chains exact offline; Revit 2026 (2024 files opened as upgrades, audit ON) opened and audited 14 of 14 chains, 4-generation overwrite chains on two projects, and 3 leaf deletes.
- Read back **by value in Revit** through the API: moves (+1 ft exactly), rotations (30.0000 degrees), Double and Int parameters, non-ASCII strings, wall and floor parameters, deleted elements missing, derived echoes (a view's Detail Level on its viewport). One edit (leader style pen weight) is stored but has no visible effect in Revit.

## What it refuses (by design, with a reason shown)
- Revit years other than 2024 and 2026 (2025 included), files whose year and build stamp disagree, damaged or relabelled files.
- Overwrite of workshared models, groups / design options, files that changed on disk, read-only files, online-only cloud placeholders, models too large to verify (unless the labelled limited verification is chosen: SAVE AS only).
- Edits the backend cannot do: Level / Grid move or rename, edits of group members, delete of anything with dependents, rotate / move of elements that live in several partitions (the viewer cannot read its own edit back; Revit does honour the newest copy, one element tested).

## Limits (not claimed)
- Two real projects with a handful of edits of each kind; 2024 files were opened as upgrades in Revit 2026, never in a 2024 Revit; one real 2026 project (a 2024 project saved by Revit 2026 in the guest: 24 chains exact, 5 audited in Revit) but no 2025 project; nothing on Windows or macOS; the real oracle gate is closed (overwrite tests used a temporary gate inside the test process); several by-value results are single elements.
- Memory: the full element verify of a 51 MB project needs between 5 and 8 GB of address space for the worker; bigger projects use the labelled limited verification (24 MB checked by value in Revit).
