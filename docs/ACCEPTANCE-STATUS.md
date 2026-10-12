# Geometry acceptance status (per class, per year; measured on all corpus .rvt files converted so far)

files per year (big files evaluated in two low-memory halves count 0.5 each): 2020: 4, 2021: 4, 2022: 4

Cell = elements n | true % | parametric-unproven % | approximate % | box-only % | IoU>=0.95 % | volume<=2% error % (n measurable). DONE = true>=95, box<=2, IoU>=95, volume>=95.

| class | year | n | true | param | approx | box | IoU>=.95 | vol<=2% | DONE |
|---|---|---|---|---|---|---|---|---|---|
| SWall | 2020 | 159 | 89 | 4 | 8 | 0 | 72 | 88 (130) | no |
| SWall | 2021 | 381 | 82 | 8 | 10 | 0 | 81 | 99 (313) | no |
| SWall | 2022 | 381 | 82 | 8 | 10 | 0 | 81 | 99 (313) | no |
| Floor | 2020 | 19 | 100 | 0 | 0 | 0 | 100 | 95 (19) | no |
| Floor | 2021 | 43 | 100 | 0 | 0 | 0 | 100 | 95 (43) | YES |
| Floor | 2022 | 43 | 100 | 0 | 0 | 0 | 100 | 95 (43) | YES |
| Ceiling | 2020 | 10 | 100 | 0 | 0 | 0 | 100 | 90 (10) | no |
| Ceiling | 2021 | 113 | 100 | 0 | 0 | 0 | 100 | 99 (113) | YES |
| Ceiling | 2022 | 113 | 100 | 0 | 0 | 0 | 100 | 99 (113) | YES |
| ProfileRoof | 2020 | 4 | 100 | 0 | 0 | 0 | 100 | 100 (4) | YES |
| ProfileRoof | 2021 | 12 | 100 | 0 | 0 | 0 | 100 | 50 (4) | no |
| ProfileRoof | 2022 | 12 | 100 | 0 | 0 | 0 | 100 | 50 (4) | no |
| FamilyInstance | 2020 | 1977 | 99 | 0 | 0 | 1 | 47 | 64 (1922) | no |
| FamilyInstance | 2021 | 11606 | 100 | 0 | 0 | 0 | 88 | 87 (11523) | no |
| FamilyInstance | 2022 | 11606 | 100 | 0 | 0 | 0 | 88 | 87 (11523) | no |
| StairsRun | 2020 | 6 | 100 | 0 | 0 | 0 | 50 | - (0) | no |
| StairsRun | 2021 | 1 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| StairsRun | 2022 | 1 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| StairsElement | 2020 | 6 | 100 | 0 | 0 | 0 | 67 | - (0) | no |
| StairsElement | 2021 | 1 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| StairsElement | 2022 | 1 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| BaseRailing | 2020 | 9 | 100 | 0 | 0 | 0 | 56 | - (0) | no |
| BaseRailing | 2021 | 44 | 100 | 0 | 0 | 0 | 55 | - (0) | no |
| BaseRailing | 2022 | 44 | 100 | 0 | 0 | 0 | 55 | - (0) | no |
| RoomElem | 2020 | 25 | 100 | 0 | 0 | 0 | 100 | 94 (17) | no |
| RoomElem | 2021 | 189 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| RoomElem | 2022 | 189 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| SiteSurface | 2020 | 10 | 100 | 0 | 0 | 0 | 90 | - (0) | no |
| SiteSurface | 2021 | 6 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| SiteSurface | 2022 | 6 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| WallSweep | 2020 | 44 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| WallSweep | 2021 | 33 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| WallSweep | 2022 | 33 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| ContFooting | 2020 | 13 | 100 | 0 | 0 | 0 | 100 | 100 (13) | YES |
| ContFooting | 2021 | 4 | 100 | 0 | 0 | 0 | 100 | 100 (4) | YES |
| ContFooting | 2022 | 4 | 100 | 0 | 0 | 0 | 100 | 100 (4) | YES |
| Hub | 2020 | 765 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| Hub | 2021 | 1386 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| Hub | 2022 | 1386 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| ReferencePoint | 2020 | 765 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| ReferencePoint | 2021 | 1386 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| ReferencePoint | 2022 | 1386 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelBeam | 2020 | 435 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelBeam | 2021 | 509 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelBeam | 2022 | 509 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelColumn | 2020 | 262 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelColumn | 2021 | 583 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelColumn | 2022 | 583 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| RebarInSystem | 2020 | 224 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| RebarInSystem | 2021 | 224 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| RebarInSystem | 2022 | 224 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| Rebar | 2020 | 133 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| Rebar | 2021 | 133 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| Rebar | 2022 | 133 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| ElementGroup | 2021 | 161 | 100 | 0 | 0 | 0 | 61 | - (0) | no |
| ElementGroup | 2022 | 161 | 100 | 0 | 0 | 0 | 61 | - (0) | no |
| AnalyticalModelIsolatedFoundation | 2020 | 78 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelIsolatedFoundation | 2021 | 78 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelIsolatedFoundation | 2022 | 78 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| FilledRegion | 2020 | 73 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| FilledRegion | 2021 | 80 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| FilledRegion | 2022 | 80 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| GStyleElem | 2020 | 43 | 0 | 0 | 0 | 100 | 42 | - (0) | no |
| GStyleElem | 2021 | 60 | 0 | 0 | 0 | 100 | 57 | - (0) | no |
| GStyleElem | 2022 | 66 | 0 | 0 | 0 | 100 | 53 | - (0) | no |
| DPart | 2020 | 45 | 100 | 0 | 0 | 0 | 100 | 100 (45) | YES |
| DPart | 2021 | 45 | 100 | 0 | 0 | 0 | 100 | 100 (45) | YES |
| DPart | 2022 | 45 | 100 | 0 | 0 | 0 | 100 | 100 (45) | YES |
| RebarSystem | 2020 | 45 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| RebarSystem | 2021 | 45 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| RebarSystem | 2022 | 45 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| LineLoad | 2020 | 35 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| LineLoad | 2021 | 35 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| LineLoad | 2022 | 35 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| BoundaryConditions | 2020 | 27 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| BoundaryConditions | 2021 | 27 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| BoundaryConditions | 2022 | 27 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| Viewer3d | 2020 | 23 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| Viewer3d | 2021 | 28 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| Viewer3d | 2022 | 28 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| AnalyticalModelBrace | 2020 | 22 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelBrace | 2021 | 22 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelBrace | 2022 | 22 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelWall | 2020 | 25 | 100 | 0 | 0 | 0 | 4 | - (0) | no |
| AnalyticalModelWall | 2021 | 15 | 100 | 0 | 0 | 0 | 7 | - (0) | no |
| AnalyticalModelWall | 2022 | 15 | 100 | 0 | 0 | 0 | 7 | - (0) | no |
| CategoryElem | 2020 | 7 | 0 | 0 | 0 | 100 | 43 | - (0) | no |
| CategoryElem | 2021 | 13 | 0 | 0 | 0 | 100 | 46 | - (0) | no |
| CategoryElem | 2022 | 14 | 0 | 0 | 0 | 100 | 36 | - (0) | no |
| AreaLoad | 2020 | 10 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AreaLoad | 2021 | 10 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AreaLoad | 2022 | 10 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| BasePoint | 2020 | 8 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| BasePoint | 2021 | 8 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| BasePoint | 2022 | 8 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelSlab | 2020 | 8 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| AnalyticalModelSlab | 2021 | 8 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| AnalyticalModelSlab | 2022 | 8 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| PropertyLineSegment | 2020 | 8 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| PropertyLineSegment | 2021 | 8 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| PropertyLineSegment | 2022 | 8 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| ShaftOpening | 2020 | 4 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| ShaftOpening | 2021 | 10 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| ShaftOpening | 2022 | 10 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| MassLevelData | 2020 | 2 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| MassLevelData | 2021 | 10 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| MassLevelData | 2022 | 10 | 100 | 0 | 0 | 0 | 0 | - (0) | no |
| Stairs | 2021 | 10 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| Stairs | 2022 | 10 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |

## Same data in the reader table's definition (NOTES.md "Per-class / per-year geometry table"), side by side

ACCURATE = mesh/solid whose volume is within 2 % of Revit's (or, without a Revit volume, bbox IoU >= 0.95); true-off = a mesh exists but fails that; own approx = our parametric/approximate rebuild (not claimed accurate); box = box only; unjudged = mesh without a reference to judge it. Reader columns are 176's numbers (partial run, other element sampling).

| class | n | viewer accurate | true-off | own approx | box | unjudged | reader accurate | reader true-off | reader box |
|---|---|---|---|---|---|---|---|---|---|
| SWall | 921 | 0 | 0 | 17 | 0 | 0 | 81.7 | 5.8 | 12.5 |
| Floor | 105 | 0 | 0 | 0 | 0 | 0 | 98.7 | 1.3 | 0.0 |
| Ceiling | 236 | 0 | 0 | 0 | 0 | 0 | 99.7 | 0.0 | 0.3 |
| ProfileRoof | 28 | 0 | 0 | 0 | 0 | 0 | 100.0 | 0.0 | 0.0 |
| FamilyInstance | 25189 | 0 | 0 | 0 | 0 | 0 | 86.3 | 10.9 | 2.8 |
| StairsRun | 8 | 0 | 0 | 0 | 0 | 0 | 33.3 | 22.2 | 44.4 |
| StairsElement | 8 | 0 | 0 | 0 | 0 | 0 | 44.4 | 11.1 | 44.4 |
| BaseRailing | 97 | 0 | 0 | 0 | 0 | 0 | 34.5 | 47.6 | 17.9 |
| RoomElem | 403 | 0 | 0 | 0 | 0 | 0 | 85.5 | 0.4 | 14.0 |
| SiteSurface | 22 | 0 | 0 | 0 | 0 | 0 | 95.5 | 0.0 | 4.5 |
| WallSweep | 110 | 0 | 0 | 0 | 0 | 0 | 96.8 | 0.0 | 3.2 |
| ContFooting | 21 | 0 | 0 | 0 | 0 | 0 | 100.0 | 0.0 | 0.0 |
| Hub | 3537 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| ReferencePoint | 3537 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| AnalyticalModelBeam | 1453 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| AnalyticalModelColumn | 1428 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| RebarInSystem | 672 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| Rebar | 399 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| ElementGroup | 322 | 0 | 0 | 0 | 0 | 0 | - | - | - |
| AnalyticalModelIsolatedFoundation | 234 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| FilledRegion | 233 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 100.0 |
| GStyleElem | 169 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| DPart | 135 | 0 | 0 | 0 | 0 | 0 | 98.9 | 0.0 | 1.1 |
| RebarSystem | 135 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| LineLoad | 105 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| BoundaryConditions | 81 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| Viewer3d | 79 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| AnalyticalModelBrace | 66 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| AnalyticalModelWall | 55 | 0 | 0 | 0 | 0 | 0 | 18.4 | 18.4 | 63.3 |
| CategoryElem | 34 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| AreaLoad | 30 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| BasePoint | 24 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| AnalyticalModelSlab | 24 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 100.0 |
| PropertyLineSegment | 24 | 0 | 0 | 0 | 100 | 0 | - | - | - |
| ShaftOpening | 24 | 0 | 0 | 0 | 0 | 0 | 100.0 | 0.0 | 0.0 |
| MassLevelData | 22 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 100.0 |
| Stairs | 20 | 0 | 0 | 0 | 0 | 0 | 100.0 | 0.0 | 0.0 |
