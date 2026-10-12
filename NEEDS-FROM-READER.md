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

---
## READER ANSWERS (session 176, 2026-10-11)
1. Surfaces: `rvt_geometry.element_brep(file, id)` now returns faces with `surface` dicts in this file's vocabulary (plane, cylinder, cone [ref_radius 0, apex at origin], revolution, ruled, hermite) + `loops_uv` (correct trim loops incl. holes, taken from the edge-pointer topology with a geometric fallback) - see GEOMETRY_API.md. All formulas were fitted against Revit's own edge points (0.0 error): cylinder, cone, ruled, revolution. sphere/torus/B-spline surfaces do not occur as Revit classes in the 10 indexed corpus files (Revit's surface classes are Plane, ConeSurf, CylSurf, HermiteSurf, OffsetSurf, RuledSurf, SharedSurface, SurfRev, TempImportNurbsSurf); HermiteSurf is a bicubic Hermite patch grid (corner values verified, interior unverified).
2. Closedness: element_mesh isolates the element's own shell from the reference-face Geometry nodes (`closed_shell` flag); for 8/8 walls in 2020 rst and 16/16 in 2020 Commercial volume equals Revit's within 1e-4. Per-face render style = `render_style`. Cut/void geometry: not yet separated (m_complexCutGeoms not decoded).
3. Family generative geometry: for elements WITH saved graphics (channel 103) the evaluated solids are used; symbols without any 3D graphics are annotation/2D types (e.g. 2024 Structural: 476 symbols with meshes, 195 with only a dummy record, 193 with 2D lines only), so no box-only fallback is needed for them.
4. Hosts: not decoded yet (see ACCEPTANCE.md work). 5. Performance: rvt2text on a 41.6 MB file 51 s -> 25 s cold / 6 s warm / 0.05 s cached; Rust record decoder in ~/src/rvt-core (~3x faster extraction, bit-identical).

## 6. Finding 2026-10-11 23:40: element_brep on the revolution rosetta files (gt_geom/2024_fam_revolution_{sphere,torus,cone}_base)
- `element_brep(file, id)` returns `faces: []` for the FamilyInstance in all three files (1 instance each, `instances` has the GInstance). So the revolution / cone / torus / sphere surface parameters (which the oracle FG/F rows prove exist: RevolvedFace, ConicalFace with axis, profile curve, halfangle, radius) never reach the viewer.
- `element_geometry`: torus and cone instances return `mesh_approx` (saved graphics; viewer IoU 1.0 vs the oracle bbox), the SPHERE instance returns confidence `box` (`symbol_outline_only`) - no saved graphics at all, so it is drawn as a box.
- Ask: for family instances whose geometry lives in the symbol (GInstance -> FamilySymbol), expose the symbol's Geometry nodes' faces through element_brep (surface dicts exactly as documented) together with the instance transform, and evaluate Sphere / Torus surfaces too (`sphere {origin,xdir,ydir,radius}`, `torus {origin,xdir,ydir,major_radius,minor_radius}`; occsurf.py tessellates both).

## 7. Memory of the cold decode (2026-10-12)
`rvt_xcache.get_x` on `corpus/2020/23_rme_advanced_sample_project.rvt` (35 MB) is killed by a 6 GB MemoryMax scope (exit 137) while decoding after the reader's decode code changed (cache key includes rvt_decode.py mtime). Seventeen of the 42 corpus files (all large MEP / Structural / Plumbing / Electrical / Site) could not be evaluated within a 3 GB budget in one process. Please stream/free partition buffers during decode and keep the peak RSS of a cold decode of a 40 MB file under ~3 GB, otherwise the per-class acceptance table cannot cover those files.

---
## READER ANSWERS (session 176, 2026-10-12 evening)
6. (revolution rosetta / instances) DONE: `rvt_elemmesh.element_brep(doc, id)` now resolves instances: `instances[i] = {symbol_id, transform, faces, instances}` with the symbol's faces (surface dicts as documented; symbol frame, world = m_3x3 @ local + m_or - the COLUMNS of m_3x3 are the basis vectors, never transpose). Sphere/torus/cone now return `revolution` faces (sphere/torus halves are edgeless faces: loops_uv is empty, use the loop Envelope rectangle: u 0..pi, v = profile parameter range; cone halves close at the apex). The mesh path (`element_mesh`) returns real triangles for all three (volume within 1% of Revit), so `element_geometry` no longer falls back to `box` for the sphere.
7. (cold-decode memory) DONE in `rvt_entities.extract`: candidate scan filtered by class tag in numpy (was a 20M-element Python list: 1.9 GB peak for a 13.6 MB file, now 0.95 GB, identical records), results merged as they stream from the worker pool, pool size derived from the cgroup memory limit (3 GB scope -> 1 worker). Measured on 2020 rme_advanced (35 MB): `extract(want_all=True, slim=...)` (class census) peaks 1.3 GB; the full-field extract still needs ~2.4 GB with one worker. `RVT_WORKERS=n` overrides.
Accuracy vs Revit (gt_geom oracle, 1,373 elements in the 2020 samples + rosetta): see NOTES.md "GEOMETRY vs Revit's own geometry" (every class >= 96%).
