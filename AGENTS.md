# Agents: querying .rvt files with rvt-ballet

To answer a question about what is inside a Revit `.rvt` file (sheets, sheet sets, views, levels, walls, doors, rooms, materials, counts), use the cold, read-only query commands. Do not use Revit, and do not convert the model:

```
rvt-ballet --help                       # command groups
rvt-ballet query --help                 # every query command
rvt-ballet sheets FILE.rvt [--json]     # or views, levels, grids, counts, elements, walls, doors, rooms, materials, ...
rvt-ballet query collect FILE.rvt --class Wall | --category Doors [--fields a,b] [--where k=v] [--json|--tsv]
```

- Each query takes about 2-4 s on a 1 GB model (`counts` and `elements` about 8 s).
- The file is never written, and an answer is never built from a read that overlapped a save (exit 75: retry).
- The full guide is docs/agent-queries.md. It covers timings, what is reliable for each class, units (feet), 20 example questions with their commands, and how to combine queries for compound questions.
- The Claude skill is skills/rvt-query/SKILL.md. `rvt-ballet install-skill` copies it into every ~/.claude* config directory.
- Project files are often confidential client data. Keep results in the session, and never copy a model into this repository or its tests.

Code map for the query engine:
- `rvtballet/fastquery.py`: the engine and the `query` CLI.
- `rvtballet/rvtfile.py`: file helpers.
- `rvtballet/stable.py`: change detection during reads.
- `rvtballet/infocli.py`: `info`, `diff`, `check` and `counts --by`.
