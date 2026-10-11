# Fresh Revit exports that would help (NOT requested to be run; for the user to decide; no VM is launched by this project)
Existing ground truth (rvt-research/gt4, groundtruth*) already covers element lists, Volume/Area/Length/Height parameters. Still missing and useful:
1. Per-element world bounding boxes + solid volumes from `Element.get_Geometry` (Options: DetailLevel Fine) for Walls, Floors, Roofs, Ceilings, Stairs, Structural Columns/Framing, Doors, Windows, for 2020/18, 2020/20, 2026/55, 2026/58. Would validate the oriented family placeholders and roof prisms (currently validated only against the bounding box stored in the .rvt header).
2. For roofs: per-element top-face plane equations (slope) so roof slopes can be checked.
3. For family instances: the instance Transform (Origin/BasisX/Y/Z) and the symbol's local bounding box, to confirm which matrix convention (columns vs rows) the file's m_3x3 uses.
4. Room boundary segments (SpatialElementBoundaryOptions) for rooms/spaces of 2020/20 and 2026/54, to check footprint outlines.
Format: TSV like gt4 (E/P rows) plus G rows: `G id minx miny minz maxx maxy maxz volume`.
