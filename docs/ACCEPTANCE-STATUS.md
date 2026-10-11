# Geometry acceptance status (per class, per year; measured on all corpus .rvt files converted so far)

files per year: 2020: 3

Cell = elements n | true % | parametric-unproven % | approximate % | box-only % | IoU>=0.95 % | volume<=2% error % (n measurable). DONE = true>=95, box<=2, IoU>=95, volume>=95.

| class | year | n | true | param | approx | box | IoU>=.95 | vol<=2% | DONE |
|---|---|---|---|---|---|---|---|---|---|
| SWall | 2020 | 153 | 0 | 56 | 44 | 0 | 23 | 21 (124) | no |
| Floor | 2020 | 14 | 0 | 100 | 0 | 0 | 100 | 100 (14) | no |
| Ceiling | 2020 | 10 | 0 | 100 | 0 | 0 | 100 | 100 (10) | no |
| ProfileRoof | 2020 | 4 | 0 | 75 | 25 | 0 | 100 | 25 (4) | no |
| FamilyInstance | 2020 | 1072 | 77 | 0 | 10 | 12 | 74 | 19 (1019) | no |
| StairsRun | 2020 | 6 | 67 | 0 | 17 | 17 | 67 | - (0) | no |
| StairsElement | 2020 | 6 | 67 | 0 | 17 | 17 | 83 | - (0) | no |
| BaseRailing | 2020 | 9 | 22 | 0 | 44 | 33 | 56 | - (0) | no |
| CurtainGridLine | 2020 | 55 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| RoomElem | 2020 | 25 | 100 | 0 | 0 | 0 | 100 | 12 (17) | no |
| SiteSurface | 2020 | 10 | 90 | 0 | 0 | 10 | 90 | - (0) | no |
| WallSweep | 2020 | 44 | 100 | 0 | 0 | 0 | 100 | - (0) | YES |
| ContFooting | 2020 | 13 | 77 | 0 | 8 | 15 | 92 | 23 (13) | no |
| RebarInSystem | 2020 | 224 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| Hub | 2020 | 218 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| ReferencePoint | 2020 | 218 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| Rebar | 2020 | 122 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| FilledRegion | 2020 | 63 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelBeam | 2020 | 60 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| AnalyticalModelColumn | 2020 | 59 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| DPart | 2020 | 45 | 100 | 0 | 0 | 0 | 100 | 87 (45) | no |
| RebarSystem | 2020 | 44 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| LineLoad | 2020 | 35 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
| Viewer3d | 2020 | 21 | 0 | 0 | 0 | 100 | 100 | - (0) | no |
| BoundaryConditions | 2020 | 20 | 0 | 0 | 0 | 100 | 0 | - (0) | no |
