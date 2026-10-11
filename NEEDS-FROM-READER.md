# What rvt-viewer would like from the rvt-research reader (nothing here is blocking; viewer works without it)
1. Family instance / symbol solids. FamilySymbol records in projects carry only `BaseFamilySymbolGStep` + a bbox; the viewer can show instances only as oriented bounding boxes.
   If the generative geometry (GExtrusion / GSweep / GBlend / GRevolve steps with their profiles and parameter expressions) of a symbol can be evaluated to faces,
   a per-symbol mesh in symbol space + the instance transform would give real shapes and allow instancing.
2. Non-planar surface types in `Geometry` bodies (CylSurf, ConeSurf, spheres, NURBS faces): `rvtviewer/brep.py` only tessellates `Plane` faces; skipped faces are counted. Decoded surface parameters are already in the records; nothing needed unless fields are missing.
3. Room/space boundaries: RoomElem has only a point + header bbox in the decoded records; if a boundary polyline (or the room's geometry bodies) is decodable it would give real room footprints.
4. Sheet->view links: `Viewport.m_dbViewId` / `m_sheetViewportElemIds` resolve for only some files (sheet "views" lists are often empty in the viewer).
5. Roof slopes: ProfileRoof/FootPrintRoof `m_slopeCurves` is empty in the samples; per-edge slope definitions (or the final roof faces) would let roofs be sloped instead of flat prisms in the bbox height range.
6. A public `load(path)` returning records+headers+params in one pass (viewer currently monkeypatches `rvt_entities.extract` to share the pass with `rvt_params.params`, see rvtviewer/reader.py).
