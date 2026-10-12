# Viewer vs Revit oracle (session 181 gt_geom / rosetta files), 2026-10-12
Measured with tools/compare_gt.py (bbox IoU and volume ratio of the viewer's mesh against Revit's exported solid); `tools/oracle_coverage.py` lists oracle elements the viewer has no geometry for.

| rosetta / oracle file | element | viewer fidelity | IoU | volume ratio |
|---|---|---|---|---|
| 2024_kwalls (plain walls) | 5 straight walls | parametric | 1.0 | 1.0 |
| 2024_wall_types_base | 7 wall types incl. multi-layer (partition, brick on stud, masonry, blockwork) | parametric, full compound-structure thickness | 1.0 | 1.0 (was 0.68-0.81 before the layer-boundary alignment) |
| 2024_wall_curved_base/var | ArcWall (no ElementHeader) | parametric (cylinder faces) | 1.0 | 0.997 |
| 2024_wall_profile_base/var | edited-profile wall (profile sketch outline) | parametric (profile polygon extruded) | 1.0 | 1.0 (was 1.18 / 1.24) |
| 2024_room_base | walls + room | walls parametric, room = reader mesh | 0.92-1.0 | 1.0 |
| 2024_stair_run_base | stair run / supports / railing | approx (base), mesh (var) | 0.85-1.0 | supports 1.0 |
| 2024_topography_base | SiteSurface (no header) | reader mesh | 1.0 | - |
| 2024_railing_base | BaseRailing | approx (reader mesh incomplete) | 0.67 | - |
| 2024_fam_revolution_torus/cone | family instance | reader mesh | 1.0 | - |
| 2024_fam_revolution_sphere | family instance | BOX (reader has no saved graphics / brep faces) | 1.0 (bbox only) | - |
| 2024_house_base | doors (2) | BOX; windows (3) approx; columns mesh; floor, walls parametric; room mesh | | |

## Sweep over all 28 rosetta files with the 2026-10-12 reader (per class; tools/compare_gt.py, one conversion at a time)
| class | n | fidelity | median IoU | volume within 2% |
|---|---|---|---|---|
| FamilyInstance | 103 | mesh 88, approx 9, box 6 | 1.00 | - |
| SWall | 30 | parametric | 0.99 | 26/28 |
| Floor | 27 | parametric | 1.00 | 27/27 |
| ArcWall | 2 | parametric | 1.00 | 2/2 |
| RoomElem | 5 | mesh | 1.00 | 5/5 |
| WallSweep | 4 | mesh | 1.00 | 2/2 |
| StairsSupport | 4 | mesh 2, approx 2 | 1.00 | 4/4 |
| StairsRun / StairsElement | 2 / 2 | mesh 1, approx 1 each | 0.99-1.00 | - |
| TopRail | 6 | mesh | 1.00 | - |
| SiteSurface | 2 | mesh | 1.00 | - |
| BaseRailing | 6 | approx 4, box 2 | 0.42 | - |
| CurtainGridLine | 7 | box | 0.00 | - |
