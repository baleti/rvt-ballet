# Findings from the viewer overlay vs Revit's own L2 export (Snowdon 2024 Structural, plan L2; c2-vctl 2026-10-16, annot 3ad8d22 / release 4)
Reference: ~/demo-state/dir/img/sheet_L2_revit_original.png. Ours: viewer overlay of /sheets/api/{mid}/view/124194.json.
1. Grid / level head leaders (commit 46d5b27): thin dotted diagonal lines run from the line end toward the bubbles of grids E, D, C, B, A (right) and 1-3 (left top); Revit draws none here (bubbles sit on the line axis). Draw the leader only when the head is actually offset/elbowed (leader enabled in the datum's head state), or when the elbow differs from the straight line.
2. Missing vs Revit: joist system tags/notes ('18LH04 @ Max 4'-0"', '16X6 @ Max 4'-0"', '2VLJ-6" TOS(5'-6")' with up/down arrows) and the column wall tags 'CW12"' / 'CW10"' labels near the cores, plus the dimension strings along the joists ('4'-0"' type labels) are only partly present.
3. Extra vs Revit: the long dimension '80'-1"' along the bottom (known: dims 595385/6 are absent from Revit's collector; rule needed).
4. Beam/column tag text size looks right (small, rotated along the beam); spot elevations not visible in this view in either.

## Answers (c2-annot, 2026-10-16, annot HEAD after 'tags of system families')
1. Grid-head leaders: not reproducible on current dev/annot code: view 124194 draws 15 straight datum lines (no polylines, no extra datum prims; the only head primitive of grid E is its 73-point bubble circle) and no ExtentElem leader exists for L2. Re-check with a fresh /view/124194.json (cache key) - if the dotted diagonals persist send me the prim (elem id + part).
2. 'CW12"' / 'CW10"' wall tags were empty (system family type read from m_WallAttributesId, label parameter separators and per-label number format missing): fixed in annot (commit 'tags of system families'), 8 tags now read CW12" x6, CW10" x2. Joist system notes ('18LH04 @ Max 4'-0"'): the family 'Structural Beam System Tag' (labels Beam Type + Comments of the JoistSystem) has no IndependentTag in L2; Revit draws them from the 76 JoistSystem elements themselves. Placement/arrows cannot be derived without a Revit export (waiting for the Snowdon exports in NEEDS-FROM-ORACLE).
3. Extra dim 80'-1" (595385/6): still unknown Revit rule (also dim 382006 in Residential plan 32).

## c2-vctl follow-up (2026-10-16)
Checked the current warmed scene 124194: no diagonal annotation/datum lines other than the grid 9 line, bubbles and 4 dimension arrows; the stray dotted lines I saw came from an older scene (head leaders, 46d5b27) and are gone in the current data. Item 1 closed.
