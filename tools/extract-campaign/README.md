# extract-campaign

Utilities from the family-extraction campaign: run `rvt-extract` over many projects, then check with Revit that the extracted `.rfa` files open. The extracted families were only a check that extraction works; no data lives in this repo.

Run a campaign in a scratch directory outside the repos (`CAMPAIGN_ROOT=~/campaigns/NAME`), keep the disk budget under 15 GB and delete it at the end.

| script | what it does |
|---|---|
| `rfa_probe.py LIST.tsv OUT.jsonl` | parse every `.rfa` in its own subprocess (5 GB cap, 300 s timeout), record version, record counts, category, errors; resumable |
| `campaign_agg.py [--write]` | year x nesting depth table of extracted / opened / failed families, failure classes, families not written (and why) |
| `census_agg.py [--json]` | per-year flat versus nested open results for one census |
| `nested_by_cat.py [--summary]` | year x category x depth table from the lift manifests and the open-check results |
| `tagscan.py DIR OUT.json` | histogram of record class tags per `.rfa` |
| `lowmem_cmp.py PROJECT.rvt OUTDIR` | `rvt-extract` with and without `--low-memory`: peak RSS, time, identical `.rfa` count |

Environment: `CAMPAIGN_ROOT` (working directory), `RVT_EXTRACT` (rvt-extract checkout), `RVT_RESEARCH` (reader checkout). Results: [docs/extraction-campaign.md](../../docs/extraction-campaign.md).

Not included: the Revit open-check driver (it runs through the private write-lab VM harness) and the per-host retry wrappers.
