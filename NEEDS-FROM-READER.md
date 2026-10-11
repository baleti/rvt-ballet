# What rvt-viewer still needs from the reader (updated 2026-10-11 after rvt_geometry 'mesh_approx')
Already consumed: analytic solids are rebuilt in the viewer itself; `rvt_geometry.element_geometry` triangle meshes ('mesh_approx', saved graphics, planar+cylindrical faces) now drive family instances, railings, stairs, sweeps, footings
(e.g. 2020 Residential: box-only 69% -> 35%); `rvt_mesh.components` decides closed vs open bodies.

## 1. Surfaces the mesh skips (flag `unsupported_faces`) - highest value
Ruled, revolved, cone, torus, spline/NURBS faces and faces with `noloops`: please tessellate them (surface parameters are in the Face.m_pSurf objects; edges carry interior points) or report per-element which faces were skipped so the viewer can show the element as 'approx' with a hole count. Cylinders with partial arcs / seams are fine today.

## 2. Closedness and per-face attributes
- per-shell `closed` + `volume` + `area` (rvt_mesh.components already does it): expose through element_geometry so the viewer can mark 'exact' only for closed shells.
- per-face material id / render style (`Face.m_renderStyleId`, material ids of the layer) so doors/windows/furniture get glass/wood/metal colours instead of the category colour.
- which triangles belong to cut/void geometry (m_complexCutGeoms) versus visible geometry, and the transform convention for symbol-local void bodies (the viewer places them with world = M @ local + origin, M = columns of Trf.m_3x3, not verified: cut bodies of hosted generics landed next to, not inside, the instance bbox).

## 3. Family generative geometry (for elements where saved graphics are absent: 121 of 194 instances in 2020 Residential still 'box')
When an instance has no saved graphics: the symbol's parametric solids with their inputs, so the viewer can build them:
- extrusions: profile loops (lines/arcs/splines in the sketch plane + plane frame), start/end offsets, parameter-driven depth;
- sweeps / swept blends: path curves + profile, profile placement;
- blends, revolves (axis, angle), voids (cut) vs solid flag, join/cut order;
- parameter values (type/instance Width/Height/Depth etc.) already evaluated to numbers, and the instance Transform including mirror/flip flags (`m_flippedX/Y`, `m_workPlaneFlipped`, hand/facing flips).

## 4. Hosts: wall/roof details not stored as numbers
- walls: top/base attachment targets with offsets (JoinToRoofGStep gives the roof ids; the offset and whether the wall reaches the roof's top or underside are unknown), profile edits (`Extrusion` step / sketch loops), layer order versus exterior side (`m_isFlipped` semantics), location-line offset, `m_wallJoinType` meaning (0/1/2) and which wall runs through a butt join (the viewer uses 'first listed in m_info');
- roofs: per-edge slope/overhang/offset (viewer reads `m_angle`, `m_definingCurve`, `m_offset` from the sketch CurveElem user data) and the roof type's compound structure per layer;
- floors: slab-edge offsets / shaft openings that cut floors (floor volume now within 5% for 93-100% of slabs, openings from Shaft/Opening elements are not applied);
- door/window rough opening sizes (type parameters Width/Height are not among the stored params; the viewer cuts the instance bounding box shrunk by a fitted 0.2 ft).

## 5. Performance
`element_geometry` is fast once the context is loaded (194 instances in 2.6 s); cold decode of a 40 MB file is ~45 s single-threaded (parallel partition decode / lazy decode would help the first open most).
