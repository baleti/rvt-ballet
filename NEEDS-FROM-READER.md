# What rvt-viewer still needs from the reader (updated 2026-10-11 after rvt_geometry 'mesh_approx')
Already consumed: analytic solids are rebuilt in the viewer itself; `rvt_geometry.element_geometry` triangle meshes ('mesh_approx', saved graphics, planar+cylindrical faces) now drive family instances, railings, stairs, sweeps, footings
(e.g. 2020 Residential: box-only 69% -> 35%); `rvt_mesh.components` decides closed vs open bodies.

## 1. Surfaces the mesh skips (flag `unsupported_faces`) - highest value. READY ON THE VIEWER SIDE: `rvtviewer/occsurf.py` tessellates every type below through OpenCascade (one unit test per type, tests/test_surfaces.py)
For each face, expose the surface as a plain dict (replace/extend `Face.m_pSurf.obj`, same place the viewer reads Plane/CylSurf today) plus the face's trim loops in the surface's (u, v) parameter space (as `rvt_mesh.face_loops_uv` already produces):
```
plane      {'type':'plane','origin':[x,y,z],'xdir':[..],'ydir':[..]}                          u,v = distance along xdir, ydir
cylinder   {'type':'cylinder','origin','xdir','ydir','radius'}                                 u = angle (rad) from xdir, v = height along xdir x ydir
cone       {'type':'cone','origin','xdir','ydir','ref_radius','semi_angle'}                    u = angle, v = distance along the generatrix from the reference circle (OCC Geom_ConicalSurface convention)
sphere     {'type':'sphere','origin','xdir','ydir','radius'}                                   u = longitude, v = latitude
torus      {'type':'torus','origin','xdir','ydir','major_radius','minor_radius'}               u,v = angles
revolution {'type':'revolution','profile':<curve>,'axis_origin':[..],'axis_dir':[..]}         u = angle about the axis, v = profile curve parameter
bspline    {'type':'bspline','poles':[[[x,y,z] per v] per u],'weights':same shape (optional, rational),'uknots','vknots','umults','vmults','udegree','vdegree'}
ruled      {'type':'ruled','curve1':<curve>,'curve2':<curve>}                                  u along the curves, v 0..1 between them
<curve>    {'type':'line','p0','p1'} | {'type':'arc','p0','mid','p1'} | {'type':'bspline','poles','degree','knots','mults'[,'weights']}
```
All lengths feet, angles radians, world coordinates (instance transform already applied) or give `transform` once per body. `m_orientFlag` stays as is. If the Revit class carries the same information under other field names (ConeSurf, RuledSurf with m_pProfileCurve1/2, revolved/NURBS classes), just list the field names and the viewer will map them: `rvtviewer/brep.py` already routes any face whose surface dict has one of these `type` values through `occsurf.tessellate_face`.

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
