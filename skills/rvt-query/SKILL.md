---
name: rvt-query
description: Answer questions about the contents of a Revit .rvt file (sheets, sheet sets, views, levels, grids, walls, floors, roofs, doors, windows, rooms, families, materials, counts per class or category, wall heights, materials and colours) quickly and read-only, WITHOUT Revit and without converting the file. Use whenever the user asks what is inside, how many of something is in, or to list or filter elements of a .rvt model, including very large (about 1 GB) project files. This tooling is still being developed: check the limits below.
---

# Querying .rvt files with rvt-ballet (cold, read-only, no Revit)

Each query reads the file directly (no index to build, no conversion, no cache) and answers in about 2-4 s even for a 1 GB project. Revit 2017-2026 files.
Status: actively developed. The query engine became the default on 2026-11-14 (`rvt-ballet query`); results marked "not yet reliable" below need care.
Full guide with 20 worked questions: docs/agent-queries.md in the rvt-ballet repository.

## Find the tool
1. `rvt-ballet` on PATH (`command -v rvt-ballet`).
2. Otherwise this checkout: `{{RVT_BALLET}}`.

`rvt-ballet --help` and `rvt-ballet query --help` list every command. `rvt-ballet CMD FILE` and `rvt-ballet query CMD FILE` are the same.
Never use `rvt-ballet open` or `convert` to answer a question about a large file: they build geometry and refuse files over 300 MB.

## Commands
FILE is the path to the .rvt. On WSL, Windows files are under /mnt/c/Users/NAME/... Quote paths that contain spaces.
- `rvt-ballet sheets FILE` : number, title, issue date, revisions, placed views per sheet. `--json` / `--tsv`.
- `rvt-ballet sheet-sets FILE` : saved sheet sets (print/publish sets) with their member sheet numbers.
- `rvt-ballet views | levels | grids FILE` : views by class (templates counted), levels with elevation (ft and m), grid names.
- `rvt-ballet counts FILE [--json]` : element counts by category and by class.
- `rvt-ballet elements FILE --tsv` : one row per element (id, class, category, owner view, family, bbox in ft).
- Ready lists: `walls wall-types floors floor-types roofs ceilings columns framing stairs railings curtain-panels doors windows furniture generic-models rooms materials families types family-instances dimensions text-notes links revisions schedules`. Rows: id, class, name, type_name, level, category.
- `rvt-ballet query collect FILE --class Wall` or `--category Doors` : the general collector (like FilteredElementCollector).
  - `--fields a,b` adds raw record fields.
  - `--where level=Level 1` filters; repeatable.
  - `--json` / `--tsv` choose the output format.
- `rvt-ballet query walls-red-material FILE` : a worked compound query (walls below 5 m with a red material in any colour property).

Prefer `--json` or `--tsv`, and summarise with python3 -c, awk, sort or uniq instead of dumping thousands of lines. For a compound question, run two or three primitives, join them on ids or type ids in python3, and show how you got the number.

## Rules
- READ-ONLY: the file is opened read-only and never written, so reading a file that Revit has open cannot damage it.
- SAVES IN PROGRESS: a read during a Revit save can see a half-written file. The tool detects this and exits 75 with "changed during read: retry" after two automatic retries; never treat that as an answer. Querying a copy of the model is also fine. A file modified in the last 5 s (or with a fresh save temp file, a `<name>_backup` folder or `.sgtmp` beside it) is waited for, then refused with exit 75 if the save goes on: wait 10 to 30 s and rerun. `--snapshot` copies the model to a private temp dir, checks the copy against the source before and after, queries the copy and deletes it (needs free disk of the file size). `--quiet-secs N` changes the wait (0 = off); `RVTBALLET_FULL_HASH=1` makes the change check hash the whole file. A file that is only partly written (exit 1, "not a complete .rvt") is also not an answer.
- PRIVACY: project files are often confidential client data. Keep results in the session, do not paste names into public places, repos or issue trackers, and never upload or copy the file elsewhere.
- Units: Revit internal units (feet) unless a field says otherwise (1 m = 3.28084 ft). Element ids are Revit ElementIds.
- Exit codes: 0 ok, 1 unreadable, 2 usage error, 75 changed during read.

## Reliability
Measured against Revit API dumps of 9 Autodesk samples (2020-2026), old/new parity on 42 samples, and Revit's own sheet export of a 984 MB project.
- Reliable:
  - sheets (number, title): 412 of 412 on the 984 MB file
  - views, levels with elevations, grids
  - element ids, and counts per class and per category
  - names, types, levels and categories of walls, wall types, floors, ceilings, roofs, family instances, mullions and panels
  - wall height, wall layers and their materials
  - material colours (about 98 percent)
- NOT yet reliable:
  - room, stair, railing and dimension names, and any parameter value (about 71 percent of parameter values decode)
  - family symbol (type) results: only about 38 percent precision
  - family category, and derived area or volume
  - sheet issue dates, revisions and sheet-set membership: decoded but not yet checked against Revit

Say so when an answer depends on these, and do not guess. If something looks wrong or empty, report which part you do not trust, with the command and its timing (`--verbose` prints timings).
