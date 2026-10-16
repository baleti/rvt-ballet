# Fidelity per class and year (reader acceptance, final corpus run)

Source: FID_TABLE_FINAL.txt (c5-geometry reader acceptance run). Judged with the reader definition: the element is "accurate" when its mesh matches Revit's own geometry (bbox IoU, Revit Volume at Fine detail for loadable families). Buckets: **reader-accurate** = true geometry that agrees with Revit; **parametric-unproven** = true geometry whose extents/volume do not (yet) agree ("true-off"); **box-only** = no decoded solid, drawn as bounding box.

## Per class (all years)

| class | n | reader-accurate | parametric-unproven | box-only | median IoU | median abs volume error |
|---|---|---|---|---|---|---|
| FamilyInstance | 14435 | 99.5% | 0.3% | 0.1% | 0.998 | 0.00% |
| CurveElem | 13743 | 99.9% | 0.0% | 0.1% | 1.000 | nan |
| RbsDuctCurve | 4943 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| RbsPipeCurve | 4400 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| SWall | 2592 | 99.3% | 0.1% | 0.6% | 0.977 | 0.00% |
| RoomElem | 1605 | 99.4% | 0.6% | 0.0% | 1.000 | 0.00% |
| RbsConduitCurve | 1356 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| RbsFlexDuctCurve | 997 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| Ceiling | 693 | 100.0% | 0.0% | 0.0% | 1.000 | 0.00% |
| WallSweep | 452 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| Floor | 442 | 100.0% | 0.0% | 0.0% | 1.000 | 0.00% |
| FilledRegion | 422 | 100.0% | 0.0% | 0.0% | 0.000 | nan |
| BaseRailing | 259 | 100.0% | 0.0% | 0.0% | 0.937 | nan |
| DPart | 184 | 99.5% | 0.0% | 0.5% | 1.000 | 0.00% |
| Stairs | 94 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| CableTray | 68 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| AnalyticalModelWall | 55 | 100.0% | 0.0% | 0.0% | 0.000 | nan |
| ProfileRoof | 55 | 100.0% | 0.0% | 0.0% | 1.000 | 0.00% |
| ContFooting | 52 | 100.0% | 0.0% | 0.0% | 1.000 | 0.00% |
| Toposolid | 42 | 97.6% | 2.4% | 0.0% | 1.000 | 0.00% |
| SweepHost | 41 | 100.0% | 0.0% | 0.0% | 0.039 | 0.00% |
| ShaftOpening | 37 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| AnalyticalModelSlab | 24 | 100.0% | 0.0% | 0.0% | 0.000 | nan |
| ExtrusionElem | 33 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| MassLevelData | 32 | 100.0% | 0.0% | 0.0% | 0.000 | nan |
| SiteSurface | 28 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| FormElem | 26 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| AnalyticalPanel | 23 | 100.0% | 0.0% | 0.0% | 0.000 | nan |
| StairsSupport | 16 | 100.0% | 0.0% | 0.0% | 0.609 | nan |
| ArcWall | 14 | 100.0% | 0.0% | 0.0% | 0.959 | 0.01% |
| Text3dElem | 13 | 76.9% | 23.1% | 0.0% | 0.957 | nan |
| SWallRectOpening | 12 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| StairsElement | 9 | 100.0% | 0.0% | 0.0% | 0.667 | nan |
| StairsRun | 9 | 100.0% | 0.0% | 0.0% | 0.667 | nan |
| BuildingPad | 9 | 100.0% | 0.0% | 0.0% | 1.000 | 0.00% |
| BlendElem | 8 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| FamilyGeomCombination | 8 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| SweepElem | 6 | 100.0% | 0.0% | 0.0% | 1.000 | nan |
| FaceRoof | 6 | 100.0% | 0.0% | 0.0% | 1.000 | 0.00% |
| TopRail | 6 | 100.0% | 0.0% | 0.0% | 1.000 | nan |

## Per class and year (accurate % / unproven % / box %, n elements)

| class | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| FamilyInstance | 100/0/0 (1980) | 100/0/0 (2279) | 99/1/0 (2254) | 100/0/0 (2284) | 99/0/0 (1908) | 99/0/0 (1865) | 99/0/0 (1865) |
| CurveElem | 100/0/0 (2156) | 100/0/0 (2411) | 100/0/0 (2408) | 100/0/0 (2400) | 100/0/0 (1456) | 100/0/0 (1456) | 100/0/0 (1456) |
| RbsDuctCurve | 100/0/0 (800) | 100/0/0 (800) | 100/0/0 (800) | 100/0/0 (800) | 100/0/0 (581) | 100/0/0 (581) | 100/0/0 (581) |
| RbsPipeCurve | 100/0/0 (800) | 100/0/0 (800) | 100/0/0 (800) | 100/0/0 (800) | 100/0/0 (400) | 100/0/0 (400) | 100/0/0 (400) |
| SWall | 99/0/1 (411) | 99/0/1 (583) | 99/0/1 (583) | 99/0/1 (583) | 100/0/0 (144) | 100/0/0 (144) | 100/0/0 (144) |
| RoomElem | 99/1/0 (343) | 99/1/0 (326) | 99/1/0 (326) | 99/1/0 (326) | 100/0/0 (50) | 100/0/0 (117) | 100/0/0 (117) |
| RbsConduitCurve | 100/0/0 (39) | 100/0/0 (39) | 100/0/0 (39) | 100/0/0 (39) | 100/0/0 (400) | 100/0/0 (400) | 100/0/0 (400) |
| RbsFlexDuctCurve | 100/0/0 (226) | 100/0/0 (226) | 100/0/0 (226) | 100/0/0 (226) | 100/0/0 (31) | 100/0/0 (31) | 100/0/0 (31) |
| Ceiling | 100/0/0 (96) | 100/0/0 (199) | 100/0/0 (199) | 100/0/0 (199) |  |  |  |
| WallSweep | 100/0/0 (44) | 100/0/0 (33) | 100/0/0 (33) | 100/0/0 (33) | 100/0/0 (103) | 100/0/0 (103) | 100/0/0 (103) |
| Floor | 100/0/0 (61) | 100/0/0 (85) | 100/0/0 (85) | 100/0/0 (85) | 100/0/0 (42) | 100/0/0 (42) | 100/0/0 (42) |
| FilledRegion | 100/0/0 (83) | 100/0/0 (91) | 100/0/0 (91) | 100/0/0 (91) | 100/0/0 (22) | 100/0/0 (22) | 100/0/0 (22) |
| BaseRailing | 100/0/0 (37) | 100/0/0 (72) | 100/0/0 (72) | 100/0/0 (72) | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) |
| DPart | 100/0/0 (45) | 100/0/0 (45) | 98/0/2 (46) | 100/0/0 (45) | 100/0/0 (1) | 100/0/0 (1) | 100/0/0 (1) |
| Stairs | 100/0/0 (16) | 100/0/0 (26) | 100/0/0 (26) | 100/0/0 (26) |  |  |  |
| CableTray | 100/0/0 (17) | 100/0/0 (17) | 100/0/0 (17) | 100/0/0 (17) |  |  |  |
| AnalyticalModelWall | 100/0/0 (25) | 100/0/0 (15) | 100/0/0 (15) |  |  |  |  |
| ProfileRoof | 100/0/0 (4) | 100/0/0 (12) | 100/0/0 (12) | 100/0/0 (12) | 100/0/0 (5) | 100/0/0 (5) | 100/0/0 (5) |
| ContFooting | 100/0/0 (13) | 100/0/0 (4) | 100/0/0 (4) | 100/0/0 (4) | 100/0/0 (9) | 100/0/0 (9) | 100/0/0 (9) |
| Toposolid |  |  |  |  | 100/0/0 (14) | 100/0/0 (14) | 93/7/0 (14) |
| SweepHost | 100/0/0 (5) | 100/0/0 (3) | 100/0/0 (3) | 100/0/0 (3) | 100/0/0 (9) | 100/0/0 (9) | 100/0/0 (9) |
| ShaftOpening | 100/0/0 (4) | 100/0/0 (10) | 100/0/0 (10) | 100/0/0 (10) | 100/0/0 (1) | 100/0/0 (1) | 100/0/0 (1) |
| AnalyticalModelSlab | 100/0/0 (8) | 100/0/0 (8) | 100/0/0 (8) |  |  |  |  |
| ExtrusionElem | 100/0/0 (6) | 100/0/0 (9) | 100/0/0 (9) | 100/0/0 (9) |  |  |  |
| MassLevelData | 100/0/0 (2) | 100/0/0 (10) | 100/0/0 (10) | 100/0/0 (10) |  |  |  |
| SiteSurface | 100/0/0 (10) | 100/0/0 (6) | 100/0/0 (6) | 100/0/0 (6) |  |  |  |
| FormElem | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (6) | 100/0/0 (6) | 100/0/0 (6) |
| AnalyticalPanel |  |  |  | 100/0/0 (23) |  |  |  |
| StairsSupport | 100/0/0 (10) | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) |  |  |  |
| ArcWall | 100/0/0 (2) |  |  |  | 100/0/0 (4) | 100/0/0 (4) | 100/0/0 (4) |
| Text3dElem | 100/0/0 (4) | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) | 0/100/0 (1) | 0/100/0 (1) | 0/100/0 (1) |
| SWallRectOpening |  | 100/0/0 (4) | 100/0/0 (4) | 100/0/0 (4) |  |  |  |
| StairsElement | 100/0/0 (6) | 100/0/0 (1) | 100/0/0 (1) | 100/0/0 (1) |  |  |  |
| StairsRun | 100/0/0 (6) | 100/0/0 (1) | 100/0/0 (1) | 100/0/0 (1) |  |  |  |
| BuildingPad | 100/0/0 (3) | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) |  |  |  |
| BlendElem | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) |  |  |  |
| FamilyGeomCombination | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) |  |  |  |
| SweepElem |  | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) |  |  |  |
| FaceRoof |  | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) |  |  |  |
| TopRail |  |  |  |  | 100/0/0 (2) | 100/0/0 (2) | 100/0/0 (2) |

## Notes from the reader

* (40176 type/symbol definition rows excluded; 798 rows judged against the same element in another year's Revit dump of the same model, because their own year's dump lacks them)
* not solids (2D / annotation / system / container classes, excluded from the solid criterion): Dimension (3), ElementGroup (843), FamilySymbol (4645), GuideGrid (18), ImportInstance (18), LegendComponent (7536), LegendComponentGRepHolder (103), RbsPipingSystem (168), SketchGrid (2292), TextNote (4992)
* sheet-like classes (zero-volume faces; counted ACCURATE when a mesh exists - validated vs the oracle): AnalyticalModelBeam (2383), AnalyticalModelColumn (2218), AnalyticalModelSlab (34), AnalyticalModelSurface (5), AnalyticalModelWall (55), AnalyticalPanel (26), FilledRegion (425), MassLevelData (32), SiteSurface (28)
* classes judged by the oracle comparison only (mesh exists; stored bbox includes child elements, Revit gives no Volume): BaseRailing (259), StairsElement (9), StairsRun (9), StairsSupport (16)
