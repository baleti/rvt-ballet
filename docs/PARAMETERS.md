# Parameter reproduction (reader, 60 corpus files 2020-2026)

Source: PARAM_TABLE_c35.txt of the reader (c7-geometry, 2026-10-20). Every parameter value the reader derives from the .rvt (no Revit running) is compared with the value Revit's own API reports for the same element, per file year. "Exact" means equal after unit conversion within the reader's tolerance.

| year | files | values | exact | exact + approx | Double | Integer | String | ElementId |
|---|---|---|---|---|---|---|---|---|
| 2020 | 6 | 1,068,534 | 96.5% | 96.7% | 90.4% | 98.2% | 95.0% | 99.6% |
| 2021 | 9 | 1,426,259 | 96.9% | 97.0% | 91.3% | 98.0% | 95.1% | 99.7% |
| 2022 | 9 | 1,438,591 | 96.9% | 97.0% | 91.4% | 98.1% | 94.7% | 99.7% |
| 2023 | 9 | 1,529,686 | 96.8% | 96.9% | 92.1% | 96.0% | 96.1% | 99.7% |
| 2024 | 9 | 1,294,307 | 95.5% | 95.7% | 89.9% | 98.0% | 97.8% | 98.7% |
| 2025 | 9 | 1,105,074 | 95.8% | 96.0% | 91.2% | 97.8% | 97.3% | 98.6% |
| 2026 | 9 | 1,113,559 | 94.5% | 94.7% | 88.4% | 97.3% | 96.8% | 98.2% |
| **all** | 60 | 8,976,010 | **96.2%** | 96.3% | | | | |

Not reproduced (share of values, per year): lookups 0.6-1.2%, geometry-derived values (Volume, Area, Length, offsets, elevations) about 1.0-1.4%, MEP 0.6-2.0%, other 0.3-1.4%.

In the viewer: the inspector's Parameters section states this figure; parameters that come from the file are shown as read, so the numbers above bound how many of the listed values could differ from Revit's schedule output. Geometry accuracy per class is in docs/FIDELITY-FINAL.md.
