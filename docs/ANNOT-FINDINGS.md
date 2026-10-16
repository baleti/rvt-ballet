# Findings from the viewer overlay vs Revit's own L2 export (Snowdon 2024 Structural, plan L2; c2-vctl 2026-10-16, annot 3ad8d22 / release 4)
Reference: ~/demo-state/dir/img/sheet_L2_revit_original.png. Ours: viewer overlay of /sheets/api/{mid}/view/124194.json.
1. Grid / level head leaders (commit 46d5b27): thin dotted diagonal lines run from the line end toward the bubbles of grids E, D, C, B, A (right) and 1-3 (left top); Revit draws none here (bubbles sit on the line axis). Draw the leader only when the head is actually offset/elbowed (leader enabled in the datum's head state), or when the elbow differs from the straight line.
2. Missing vs Revit: joist system tags/notes ('18LH04 @ Max 4'-0"', '16X6 @ Max 4'-0"', '2VLJ-6" TOS(5'-6")' with up/down arrows) and the column wall tags 'CW12"' / 'CW10"' labels near the cores, plus the dimension strings along the joists ('4'-0"' type labels) are only partly present.
3. Extra vs Revit: the long dimension '80'-1"' along the bottom (known: dims 595385/6 are absent from Revit's collector; rule needed).
4. Beam/column tag text size looks right (small, rotated along the beam); spot elevations not visible in this view in either.
