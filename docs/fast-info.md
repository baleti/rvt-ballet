# Fast admin data (superseded)

On 2026-11-14 the streamed single-process scan that this page described (`fastinfo.scan`: chain blocks, 3 MB windows, 96 MB worker segments, a result cache) was replaced by the parallel query engine `rvtballet/fastquery.py`.

The commands are the same and run cold:
- `rvt-ballet sheets | sheet-sets | views | levels | grids | counts | elements FILE`;
- `info` (header only) is unchanged;
- `diff`, `check` and `counts --by` stay in `rvtballet/infocli.py`.

See docs/agent-queries.md for commands, timings, reliability and the old/new parity sweep.

Kept from the old page:
- `info` prints the last saved by/when from Global/DocumentIncrementTable.
- `diff BEFORE AFTER [--allow IDS] [--deep IDS] [--all-records] [--ops ops.json]` compares at the element-header level (exit 1 on unexpected changes). It is a pre-filter before the Revit VM open, not a replacement for it.
- `check FILE` runs the save gate's own integrity check (page ECC, gzip CRC/size, container walk) on files up to 150 MB.
- `convert` and `open` refuse files above 300 MB (`RVT_BIG_MB`) unless `--force`.
