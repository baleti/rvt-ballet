# Family extraction campaign: aggregate results

`rvt-extract` writes each family of a project as a standalone `.rfa`. A campaign over a large set of real projects (Revit 2019 to 2025) checked that this works: every extracted family was opened in Revit 2024 where a check was run. Only aggregates are kept here; the extracted files were deleted.

## Opened by Revit year and nesting depth (Revit 2024 open check)

Extracted: 9249 `.rfa`. Checked: 2400. Opened: 2398. Failed: 2 (both "Opening was canceled", 2020 projects). The unchecked rows were not sampled, not failures.

| year | depth | opened | failed | not yet checked | extracted |
|---|---|---|---|---|---|
| 2019 | d0 | 21 | 0 | 1384 | 1405 |
| 2019 | d1 | 4 | 0 | 185 | 189 |
| 2019 | d2+ | 0 | 0 | 92 | 92 |
| 2020 | d0 | 292 | 1 | 588 | 881 |
| 2020 | d1 | 23 | 0 | 115 | 138 |
| 2020 | d2+ | 43 | 1 | 33 | 77 |
| 2021 | d0 | 0 | 0 | 1010 | 1010 |
| 2021 | d1 | 0 | 0 | 41 | 41 |
| 2021 | d2+ | 0 | 0 | 14 | 14 |
| 2022 | d0 | 1197 | 0 | 408 | 1605 |
| 2022 | d1 | 278 | 0 | 166 | 444 |
| 2022 | d2+ | 62 | 0 | 30 | 92 |
| 2023 | d0 | 334 | 0 | 1248 | 1582 |
| 2023 | d1 | 114 | 0 | 274 | 388 |
| 2023 | d2+ | 30 | 0 | 97 | 127 |
| 2024 | d0 | 0 | 0 | 650 | 650 |
| 2024 | d1 | 0 | 0 | 118 | 118 |
| 2024 | d2+ | 0 | 0 | 21 | 21 |
| 2025 | d0 | 0 | 0 | 280 | 280 |
| 2025 | d1 | 0 | 0 | 79 | 79 |
| 2025 | d2+ | 0 | 0 | 16 | 16 |

## Families not written, by reason

| count | year | reason |
|---|---|---|
| 200 | 2020 | error: KeyError |
| 163 | 2019 | in-place family (no standalone `.rfa` exists) |
| 99 | 2020 | in-place family |
| 62 / 56 / 47 / 47 / 45 / 23 / 7 | 2019 / 2022 / 2023 / 2024 / 2020 / 2021 / 2025 | system or loadable element without an `.rfa` (mullions, panels) |

## Nested families in the earlier census (opened / checked / lifted)

| year | kind | opened | checked | lifted |
|---|---|---|---|---|
| 2019 | flat | 200 | 201 | 2910 |
| 2019 | depth 1 | 0 | 202 | 823 |
| 2019 | depth 2 | 0 | 20 | 265 |
| 2019 | depth 3+ | 0 | 2 | 8 |
| 2020 | flat | 26 | 26 | 1506 |
| 2020 | depth 1 | 0 | 28 | 399 |
| 2020 | depth 2 | 0 | 0 | 90 |
| 2020 | depth 3+ | 0 | 0 | 17 |
| 2022 | flat | 18 | 18 | 1982 |
| 2022 | depth 1 | 7 | 7 | 878 |
| 2022 | depth 2 | 0 | 0 | 62 |
| 2022 | depth 3+ | 2 | 2 | 38 |
| 2023 | flat | 0 | 0 | 35 |
| 2023 | depth 1 | 0 | 0 | 4 |
| 2023 | depth 2 | 0 | 0 | 2 |

Note: this table comes from the experimental lift of all families, which includes old-format nested families (the ones Revit rejects, see below); the table above covers the default lift.

## Findings on old-format (2017 to 2023, 4-byte id) nested families

- Flat families: 121 of 121 opened in Revit 2024. Nested: 12 of 59. Every failure nests other families.
- The Revit journal of a failing file reports a content document with no owner family, then an archive exception (code 105) and a corrupt element stream.
- Tried without effect: element table row dates, the nested document `m_last` counter, `m_originalElementId`, content record history, a small document index table.
- Real nested families of the same year have the same segment shapes as ours (content documents, big2small map, family record, owner family id); the difference left to find is the packaging (single partition, a 141 byte document index table, per-document Latest format).
- Default after the campaign: old-format flat families are written, nested ones are skipped (78 written, 17 skipped in the gate sample).

Scripts: [tools/extract-campaign](../tools/extract-campaign/README.md).
