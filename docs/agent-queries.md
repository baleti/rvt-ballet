# Querying .rvt files: guide for agents (and people)

`rvt-ballet` answers questions about the contents of a Revit `.rvt` file directly from the file. It needs no Revit, builds no index, converts nothing and keeps no cache. Each query reads the file cold and read-only.

A fresh Claude session finds this tooling through the `rvt-query` skill (`rvt-ballet install-skill`), and through the AGENTS.md / CLAUDE.md section at the repository root.

**Read-only guarantee:** every query opens the .rvt with `O_RDONLY` and never writes to it. `tests/test_query_cli.py` runs the main commands with write-mode opens of the file made to fail.

## Calling it

```
rvt-ballet CMD FILE.rvt [--json | --tsv] [options]      # same as: rvt-ballet query CMD FILE.rvt ...
rvt-ballet --help                                        # every command group
rvt-ballet query --help                                  # every query command and option
```

`FILE` is any path. Quote it when it contains spaces.
- **WSL:** Windows files are under `/mnt/c/Users/NAME/...`. Reading through the 9p mount works, but it is slower than a local copy. Copy the file into the Linux file system first when you will run many queries against it. Measured on a 22 MB Autodesk sample: `sheets` took 1.12 s through `/mnt/c` and 0.33 s on a local copy, and `counts` 0.75 s and 0.44 s. The output was identical, and the file's sha256 and mtime were unchanged after the reads.
- **Files Revit has open:** reading such a file is safe for the file, because the tool never writes and only opens it for reading.
- **Saves in progress:** a read that overlaps a Revit save can see a mix of two versions. The tool then answers `changed during read: retry` (exit code 75, nothing on stdout) after two automatic retries (`RVT_Q_RETRIES`), and never returns an answer built from such a read. This detection lives in `rvtballet/stable.py`.

### Exit codes
| code | meaning |
|---|---|
| 0 | ok |
| 1 | unreadable or damaged file (one line on stderr) |
| 2 | usage error |
| 75 | the file changed during the read |

When some compressed blocks fail their gzip CRC, the command prints a `WARNING` on stderr.

### Memory
Memory is budgeted by `RVT_Q_MEM_GB` (default 3). The budget sets the number of worker processes: about 20 on a big machine, 8 under `RVT_Q_MEM_GB=0.9`. `RVT_Q_WORKERS=N` sets the number directly.

## Commands, cost and reliability

Timings: cold, a 984 MB Revit 2024 project file, 20 workers on a 28-thread machine, 2 runs each (both runs listed).

| command | what | wall | CPU | peak PSS |
|---|---|---|---|---|
| `sheets` | number, title, issue date, drawn/approved by, revisions, placed views | 2.2 s | 33 s | 1.4 GB |
| `sheet-sets` | saved print/publish sheet sets with member sheet numbers and views | 2.6 s | 40 s | 1.4 GB |
| `views` | views by class (templates counted; `--json` lists them with scale) | 2.6 s | 41 s | 1.4 GB |
| `levels` | name, elevation (ft and m) | 2.6 s | 41 s | 1.4 GB |
| `grids` | names | 2.6 s | 41 s | 1.4 GB |
| `counts` | elements by category and by class, view-owned (2D) count | 7.6 s | 114 s | 2.6-2.7 GB |
| `elements` | one row per element: id, class, category, owner view, family, bbox (ft) | 8.6-8.7 s | 115 s | 2.5-2.6 GB |
| `walls` | id, class, name, type, level, category | 3.2 s | 56 s | 1.1 GB |
| `wall-types` | type names (+ `--fields layers` for the compound structure) | 2.8 s | 43 s | 1.3 GB |
| `doors` (any loadable-family category) | instances with type, level | 4.2 s | 68 s | 1.6 GB |
| `rooms` | room elements (names: see limits) | 2.8 s | 43 s | 1.3 GB |
| `materials` | material names and colours | 2.2 s | 37 s | 1.1 GB |
| `walls-red-material` | benchmark compound query (below) | 1.8 s | 30 s | 1.1 GB |

Other ready lists: `floors floor-types roofs ceilings columns framing stairs railings curtain-panels windows furniture generic-models families types family-instances dimensions text-notes links revisions schedules`.

The general collector is `rvt-ballet query collect FILE --class CLASS` and/or `--category NAME`. It works like Revit's FilteredElementCollector:
- CLASS is a Revit API class name (Wall, Floor, FamilyInstance, View, Room, ...) or a schema class; subclasses are included.
- `--fields a,b` adds raw record fields.
- `--where key=value` keeps only rows whose row key equals the value; it can be repeated.

### Reliability
Measured against Revit API dumps of 9 Autodesk samples (2020-2026), old/new parity on 42 samples, and Revit's own sheet export of the 984 MB file.

| data | status |
|---|---|
| sheets: number, title | **exact**: 412 of 412 equal Revit's export on the 984 MB file, 0 extra; equal on every sample 2017-2026 |
| sheets: placed views | equal to the full parser on samples |
| sheets: issue date, revisions | decoded, not yet checked against Revit |
| sheet sets | decoded (members resolved 40 of 40 on the 984 MB file), not yet checked against Revit |
| views, levels (with elevation), grids, revisions list, phases | equal to the old reader on 42 samples except where the old one was wrong (see parity) |
| element ids; counts per class and per category | ids identical to the old reader (744,802 on 42 samples, 303,008 on the 984 MB file); 7 of 744,802 headers (samples) and 51 of 303,008 (984 MB file) get a different category than the old reader picked |
| walls, wall types, floors, ceilings, roofs, family instances, mullions, panels: name, type, level, category | 100% recall and field agreement vs Revit on 9 samples |
| wall height | exact (775 of 775 walls on samples; computed from levels when the top is constrained) |
| wall layers and their materials; material colours | 127 of 127 types; 298 of 305 materials |
| room / stair / railing / dimension names, any parameter value | **not reliable** (stored as parameters; about 71% decode) |
| family symbols (`types`), family category | **not reliable** (symbol precision about 38%) |
| areas, volumes, derived quantities | **not available** |

Units are Revit internal units: lengths in feet (1 m = 3.28084 ft), angles in radians. `levels` and the `elements` bbox say "ft" explicitly. Ids are Revit ElementIds.

## 20 questions and the commands that answer them

| # | question | command |
|---|---|---|
| 1 | How many sheets are there, and what are they? | `rvt-ballet sheets F` |
| 2 | Which sheets are in a given publish set? | `rvt-ballet sheet-sets F` |
| 3 | Which views are placed on sheet A101? | `rvt-ballet sheets F --json \| python3 -c "import json,sys; print([s['views'] for s in json.load(sys.stdin) if s['number']=='A101'])"` |
| 4 | Which sheets were issued on a given date? | `rvt-ballet sheets F --tsv \| awk -F'\t' '$4=="02/03/15"'` (issue dates: unverified) |
| 5 | How many floor plans, sections and 3D views are there? | `rvt-ballet views F --json \| python3 -c "import json,sys,collections; print(collections.Counter(v['class'] for v in json.load(sys.stdin) if not v['template']))"` |
| 6 | What are the levels and their heights in metres? | `rvt-ballet levels F` |
| 7 | How many grids are there? | `rvt-ballet grids F \| wc -l` |
| 8 | How many walls, doors and windows are there? | `rvt-ballet counts F --json` then read `by_category` for Walls, Doors, Windows |
| 9 | How many walls of each type are there? | `rvt-ballet walls F --tsv \| cut -f4 \| sort \| uniq -c \| sort -rn` |
| 10 | How many walls are on each level? | `rvt-ballet walls F --tsv \| cut -f5 \| sort \| uniq -c` |
| 11 | Which wall types exist, and what are their layers? | `rvt-ballet query collect F --class WallType --fields layers --json` |
| 12 | How many doors are on Level 1? | `rvt-ballet doors F --where "level=Level 1" --tsv \| tail -n +2 \| wc -l` |
| 13 | Which door types are used, and how many of each? | `rvt-ballet doors F --tsv \| cut -f4 \| sort \| uniq -c` |
| 14 | Which materials are there, and what colour are they? | `rvt-ballet materials F --json` (fields `material`, `asset_colors`) |
| 15 | How many walls are lower than 5 m and use a red material? | `rvt-ballet query walls-red-material F` |
| 16 | How many furniture items are there per level? | `rvt-ballet furniture F --tsv \| cut -f5 \| sort \| uniq -c` |
| 17 | Which Revit links are loaded? | `rvt-ballet links F` |
| 18 | How many 2D annotation elements are there? | `rvt-ballet counts F --json` (`view_owned_elements`) |
| 19 | Which elements have a bounding box above 30 m? | `rvt-ballet elements F --tsv \| awk -F'\t' '{split($6,b," "); if (b[6] > 30/0.3048) print $1, $2, $3}'` |
| 20 | Which revisions exist, and what are their dates? | `rvt-ballet revisions F --json`, or the `revisions` field of `rvt-ballet sheets F --json` (unverified) |

Questions the tool cannot answer reliably yet: room names and areas, any parameter value (fire rating, comments, marks), family type parameters, and quantities. Say so in your answer instead of guessing.

## Combining primitives for compound questions

Run each primitive once with `--json`, then join the results in python3 by `id`, `type_id`, `level_id` or material id. For example, to find walls whose type has a layer thicker than 300 mm:

```
rvt-ballet walls F --json > walls.json
rvt-ballet query collect F --class WallType --fields layers --json > types.json
python3 - <<'EOF'
import json
T = {t['id']: t for t in json.load(open('types.json'))}
thick = {i for i, t in T.items() if any((L[0] or 0) * 0.3048 > 0.3 for L in t.get('layers') or [])}
print(sum(1 for w in json.load(open('walls.json')) if w['type_id'] in thick))
EOF
```

`walls-red-material` (in rvtballet/fastquery.py) is the worked example of a compound query done in one pass:
1. walls with their height, computed from the levels when the top is constrained;
2. joined to each wall's type and its compound-structure layers;
3. joined to each layer's material, checking every colour property: graphics colour, pattern colours, appearance asset, connected textures.

Report how you got the number: the commands, the join and the time each step took.

## Parity with the old reader (2026-11-14)

The old single-process streamed scan (`fastinfo.scan`) was replaced by `fastquery.scan`.

**Autodesk samples, Revit 2020-2026, 42 files.** Identical:
- sheets, views, grids and revisions;
- the element id set (744,802 ids);
- class counts on 41 of 42 files.

Every difference, with the verdict from the Revit dumps:

| difference | files | verdict |
|---|---|---|
| level elevations: old 0 of 332, new 328 of 328 | all | new is right (the old reader lost `m_pSurface` behind the geometry stop) |
| one nameless id-0 level (old only) | 1 | new is right: an empty false record, not a level |
| one empty id-0 revision (new only, before a fix) | 1 | fixed: empty id-0 records are dropped |
| 7 element headers: a category or class picked from another header candidate | 5 | old is right where Revit lists the element (3 of 3 checked: Revit says no category); kept as a known difference (0.001%) |

**The 984 MB project file:**
- **Sheets:** the new reader lists 413 and the old one 394; on an earlier save, 412 of 412 match Revit's export. The old reader skipped real sheets because of an ElemTable column it took for group ownership, and it kept stale first records.
- **Views:** 54 more drafting views and 20 newer names, for the same reason.
- **Identical:** levels, grids, revisions and the element ids.
- **Categories:** 51 elements get a different category.
- **Time:** 7.3 s instead of 63 s.

Nothing needed a `--legacy` flag.
- **Removed:** the per-file result cache (`~/.cache/rvt-ballet/info-*`, still used by `diff` and `counts --by`) and the `RVT_INFO_WINDOW_MB`, `RVT_INFO_WORKERS`, `RVT_INFO_SEG_MB`, `RVT_INFO_STALL` settings.
- **Shim:** `rvtballet/fastinfo.py` remains for one release. It forwards `scan()` to fastquery and re-exports the file helpers, which now live in `rvtballet/rvtfile.py`.
