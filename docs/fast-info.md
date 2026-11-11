# Fast admin data: `rvt-ballet info | sheets | views | levels | grids | counts | elements FILE`

Reads the administrative content of a .rvt (version, worksharing, project info, sheets with their views, views, levels, grids, element counts by category/class, a per-element table) **without converting the model**. Streamed, hard memory cap, never imports the geometry pipeline.

| command | what | cost |
|---|---|---|
| `info FILE` | Revit format/build, worksharing, central path, username, last save path, file mtime, project title, editors | ~0.2 s, no partition touched |
| `info FILE --levels --grids --views` | the lists below | full scan (cached) |
| `sheets FILE` | number, title, issue date, views placed on each | full scan (cached) |
| `views`, `levels`, `grids` | name, class, elevation | full scan (cached) |
| `counts FILE [--json]` | elements by category and by class, sorted keys (diffable between saves) | full scan (cached) |
| `elements FILE [--tsv\|--json] [--limit N]` | id, class, category, owner view (2D elements), family id, bbox (ft) | full scan (cached) |

All but plain `info` accept `--json` and `--refresh`. The first scan of a file is cached under `~/.cache/rvt-ballet/info-<key>.json/.npz` (key = path, size, mtime), later subcommands are instant.
`info --save` keeps the old save-gate report.

## How it stays small
* `fastinfo.chain_blocks` reads the CFB sector chain from the file in blocks (olefile would load a 770 MB partition stream into RAM); `members` inflates one gzip member at a time (offset based, 64 KB slices); `windows` joins members into 3 MB windows with 1 MB overlap.
* Each window goes to the Rust `RecDecoder.extract_chunk` (rvt-core); only the element header (category, owner view, family, bbox, class tag `m_classDef.m_ref - 12`) is kept as numpy columns; full records only for Level, Grid, DBView*, Viewport, ProjectPhase, ProjectInfo, and those are reduced to the few fields the lists need.
* Big partitions are cut into 96 MB (stored) segments, each decoded by a fresh worker process (resets allocator state; the master stays ~150 MB). The whole run sits in a memory-capped child (`RVT_INFO_MEM_GB`, default 0.9; systemd scope / Job Object).
* `convert` and `open` refuse files above 300 MB (`RVT_BIG_MB`) unless `--force`.

## Honest limits
* The ElementHeaders of a big central file are spread over the whole partition, so a full scan reads every byte: a 915 MB file takes minutes, not seconds (see c3x-progress RVTINFO lines). `info` alone is instant.
* Level / phase / workset per element are NOT available yet: they live in the full element records (m_assocLevelId, m_createdPhaseId, worksets), which this reader does not decode (would need records, not headers). Header columns only.
* Counts equal `rvt_entities.parse()` on 9 of 10 Autodesk/real seed files; the 10th differs by one element whose header the reference reader decodes with a garbage category (65536) and the windowed read decodes correctly. Window size 3 MB / overlap 1 MB may lose ~1 header in 28 000 vs 6/2 MB.
* Sheet revision and "last saved when" are not extracted (file mtime is shown).
